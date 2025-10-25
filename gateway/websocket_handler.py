"""
websocket_handler.py - WebSocket connection handling for the Gateway service

Manages WebSocket client connections, message parsing, and communication.
Handles audio streaming, language settings, and status messages.
"""

import json
import logging
import asyncio
import uuid
from typing import Dict, Any, Optional
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK, WebSocketException

from session import SpeechSession
from config import DEFAULT_SOURCE_LANGUAGE, DEFAULT_TARGET_LANGUAGE


class WebSocketHandler:
    """Handles WebSocket client connections and message processing"""

    def __init__(self, gateway_service, redis_client, audio_processor):
        self.gateway_service = gateway_service
        self.redis_client = redis_client
        self.audio_processor = audio_processor
        self.logger = logging.getLogger(f"GATEWAY-{gateway_service.instance_id}")

    async def handle_client(self, websocket):
        """Handle individual client connection with authentication"""
        # Extract token from query parameters
        from urllib.parse import urlparse, parse_qs
        try:
            path = websocket.path
            query_params = parse_qs(urlparse(path).query)
            token = query_params.get('token', [None])[0]

            if not token:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Authentication required"
                }))
                return

            # Verify JWT token
            user_data = self.gateway_service.auth_middleware.verify_token(token)
            client_id = f"client_{user_data['user_id']}_{uuid.uuid4().hex[:4]}"

        except ValueError as e:
            await websocket.send(json.dumps({
                "type": "error",
                "message": str(e)
            }))
            return
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Authentication failed"
            }))
            return

        # Initialize per-client state
        with self.gateway_service.client_lock:
            self.gateway_service.connected_clients[client_id] = websocket
            self.gateway_service.metrics["clients_connected"] += 1
        # Initialize per-client flow control
        self.redis_client.job_in_flight[client_id] = False
        self.redis_client.latest_segment_id_sent[client_id] = -1

        self.logger.info(f"Authenticated client {client_id} connected")

        # Subscribe to this client's result channel
        await self.redis_client.subscribe_to_client_channel(client_id, self.forward_result_to_client)

        self.logger.info(f"Client {client_id} ready")
        try:
            # Send initial status
            await self._send_initial_status(websocket, client_id)

            # Handle incoming messages
            await self._handle_messages(websocket, client_id)

        except ConnectionClosedError as e:
            # Normal WebSocket disconnection - log as info, not error
            self.logger.info(f"[GATEWAY-{self.gateway_service.instance_id}] Client {client_id} disconnected normally: {e}")
        except ConnectionClosedOK as e:
            # Clean WebSocket closure - log as info
            self.logger.info(f"[GATEWAY-{self.gateway_service.instance_id}] Client {client_id} closed connection cleanly: {e}")
        except WebSocketException as e:
            # Other WebSocket-related errors
            self.logger.warning(f"[GATEWAY-{self.gateway_service.instance_id}] Client {client_id} WebSocket error: {e}")
            self.gateway_service.metrics["errors"] += 1
        except Exception as e:
            # Unexpected errors - these should be logged as errors
            self.logger.error(f"[GATEWAY-{self.gateway_service.instance_id}] Client {client_id} unexpected error: {e}")
            self.gateway_service.metrics["errors"] += 1
        finally:
            await self._cleanup_client(client_id, websocket)

    async def _send_initial_status(self, websocket, client_id):
        """Send initial status message to client"""
        status_msg = {
            "type": "status",
            "client_id": client_id,
            "source_language": DEFAULT_SOURCE_LANGUAGE,
            "target_language": DEFAULT_TARGET_LANGUAGE,
            "translation_enabled": True
        }
        self.logger.debug(f"[INITIAL_STATUS] Sending initial status to client {client_id}: {status_msg}")
        try:
            await websocket.send(json.dumps(status_msg))
            self.logger.debug(f"[INITIAL_STATUS_SENT] Initial status sent to client {client_id}")
        except ConnectionClosedError:
            self.logger.info(f"Client {client_id} disconnected during initial status send")
            raise
        except Exception as e:
            self.logger.error(f"Error sending initial status to client {client_id}: {e}")
            raise

    async def _handle_messages(self, websocket, client_id):
        """Handle incoming messages from client"""
        async for message in websocket:
            if isinstance(message, (bytes, bytearray)):
                await self._handle_audio_message(message, client_id, websocket)
            else:
                await self._handle_text_message(message, client_id, websocket)

    async def _handle_audio_message(self, message, client_id, websocket):
        """Handle binary audio message from client"""
        try:
            # Parse audio message: [4 bytes metadata length][metadata JSON][audio data]
            metadata_length = int.from_bytes(message[:4], byteorder='little', signed=False)
            metadata_json = message[4:4+metadata_length].decode('utf-8')
            metadata = json.loads(metadata_json)
            sample_rate = int(metadata['sampleRate'])
            audio_chunk = message[4+metadata_length:]

            self.logger.debug(f"[AUDIO_RECEIVED] Client {client_id} sent audio chunk: {len(audio_chunk)} bytes at {sample_rate}Hz, total message: {len(message)} bytes")

            if not audio_chunk:
                self.logger.debug(f"[AUDIO_EMPTY] Client {client_id} sent empty audio chunk, skipping")
                return

            # Apply enhanced audio processing (resampling + quality improvements)
            # Use thread pool to avoid blocking the event loop
            import asyncio
            loop = asyncio.get_event_loop()
            processed_audio = await loop.run_in_executor(None, self.audio_processor.process_audio_chunk, audio_chunk, sample_rate)

            self.logger.debug(f"[AUDIO_PROCESSED] Client {client_id} audio enhanced: {len(audio_chunk)} -> {len(processed_audio)} bytes")

            # Process audio chunk
            speech_ended = await self.gateway_service.process_audio_chunk(client_id, processed_audio)

            # Note: utterance_end is now sent with final transcription results, not immediately when speech ends

        except Exception as e:
            self.logger.error(f"[GATEWAY-{self.gateway_service.instance_id}] Error processing audio from {client_id}: {e}")
            self.gateway_service.metrics["errors"] += 1

    async def _handle_text_message(self, message, client_id, websocket):
        """Handle text message from client"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")
            self.logger.debug(f"[TEXT_MESSAGE] Client {client_id} sent text message: type={msg_type}")

            if msg_type == "set_langs":
                await self._handle_set_languages(data, client_id, websocket)
            elif msg_type == "get_status":
                await self._handle_get_status(client_id, websocket)
            elif msg_type == "start_over":
                await self._handle_start_over(client_id)

        except json.JSONDecodeError:
            pass

    async def _handle_set_languages(self, data, client_id, websocket):
        """Handle language settings change"""
        # Load session and update language settings
        session = await self.redis_client.load_session(client_id)
        old_source = session.source_lang
        old_target = session.target_lang
        new_source = data.get("source_language", session.source_lang)
        new_target = data.get("target_language", session.target_lang)

        # Only update and send status if languages actually changed
        if new_source != old_source or new_target != old_target:
            session.source_lang = new_source
            session.target_lang = new_target
            session.translation_enabled = (session.source_lang != session.target_lang)
            self.logger.debug(f"[LANGUAGE_UPDATE_DETAILS] Client {client_id} language change: {old_source}->{old_target} -> {session.source_lang}->{session.target_lang}, translation_enabled: {session.translation_enabled}")
            await self.redis_client.save_session(client_id, session)

            self.logger.info(f"[GATEWAY-{self.gateway_service.instance_id}] Language updated for {client_id}: {session.source_lang} -> {session.target_lang}")

            await self._send_status_update(websocket, client_id, session)
        else:
            self.logger.debug(f"[LANGUAGE_NO_CHANGE] Client {client_id} language update requested but no change: {old_source}->{old_target}")

    async def _handle_get_status(self, client_id, websocket):
        """Handle status request"""
        session = await self.redis_client.load_session(client_id)
        await self._send_status_update(websocket, client_id, session)

    async def _handle_start_over(self, client_id):
        """Handle start over command"""
        self.logger.info(f"Client {client_id} sent start_over")
        # Clear current buffers and reset speech session WITHOUT sending any final job
        session = await self.redis_client.load_session(client_id)
        had_buffer = len(session.audio_buffer) > 0
        had_pre_speech = len(session.pre_speech_buffer) > 0
        job_was_in_flight = self.redis_client.job_in_flight.get(client_id, False)

        self.logger.debug(f"[START_OVER_RESET] Client {client_id} resetting session - buffer: {len(session.audio_buffer)} bytes, pre-speech: {len(session.pre_speech_buffer)} bytes, job in flight: {job_was_in_flight}")

        session.end_speech_session()
        await self.redis_client.save_session(client_id, session)
        # Mark job as not in flight
        self.redis_client.job_in_flight[client_id] = False

        self.logger.info(f"Client {client_id} start_over completed")
        self.logger.info(f"Start over received for {client_id}; cleared buffer (had_buffer={had_buffer})")

    async def _send_utterance_end(self, websocket, client_id):
        """Send utterance end signal to client"""
        self.logger.info(f"Speech ended for client {client_id}")
        try:
            await websocket.send(json.dumps({
                "type": "utterance_end",
                "client_id": client_id
            }))
            self.logger.debug(f"Utterance_end sent to client {client_id}")
        except ConnectionClosedError:
            self.logger.info(f"Client {client_id} disconnected during utterance_end send")
            raise
        except Exception as e:
            self.logger.error(f"Error sending utterance_end to client {client_id}: {e}")
            raise

    async def _send_status_update(self, websocket, client_id, session):
        """Send status update to client"""
        status_msg = {
            "type": "status",
            "client_id": client_id,
            "source_language": session.source_lang,
            "target_language": session.target_lang,
            "translation_enabled": session.translation_enabled
        }
        self.logger.debug(f"[LANGUAGE_UPDATE_STATUS] Sending updated status to client {client_id}: {status_msg}")
        try:
            await websocket.send(json.dumps(status_msg))
            self.logger.debug(f"[LANGUAGE_UPDATE_STATUS_SENT] Status sent successfully to client {client_id}")
        except ConnectionClosedError:
            self.logger.info(f"Client {client_id} disconnected during set_langs status send")
            raise
        except Exception as e:
            self.logger.error(f"Error sending set_langs status to client {client_id}: {e}")
            raise

    async def forward_result_to_client(self, result_data: Dict[str, Any]):
        """Forward result to the appropriate client when eligible"""
        client_id = result_data.get("client_id")
        segment_id_str = result_data.get("segment_id", "0")
        try:
            segment_id = int(segment_id_str)
        except Exception:
            segment_id = 0

        if not client_id:
            return

        # Load session to determine translation gating
        session = await self.redis_client.load_session(client_id)
        translation_enabled = bool(session.translation_enabled)
        is_translation_result = bool((result_data.get("translation") or "").strip())

        # Always accept results - both STT and translation results should be processed
        # But only unlock job for next processing when appropriate:
        # - If translation disabled: unlock after STT result (single layer)
        # - If translation enabled: unlock only after translation result (double layer)
        should_unlock_job = (not translation_enabled) or is_translation_result

        last_sent = self.redis_client.latest_segment_id_sent.get(client_id, -1)
        
        # Forward result if:
        # - Translation disabled: Forward all new STT results (single layer)
        # - Translation enabled: Forward ONLY translation results (double layer, skip STT-only)
        if translation_enabled:
            # When translation is enabled, only forward results that have translation text
            # This ensures we skip STT-only results and only send the complete translation results
            should_forward = (segment_id > last_sent) and is_translation_result
        else:
            # When translation is disabled, forward all new segments
            should_forward = (segment_id > last_sent)
        
        self.logger.debug(f"[RESULT_FILTER] Client {client_id}: segment_id={segment_id}, last_sent={last_sent}, is_translation={is_translation_result}, translation_enabled={translation_enabled}, should_forward={should_forward}")

        if should_forward:
            # Print received from worker messages
            if is_translation_result:
                translation_text = result_data.get("translation", "")
                self.logger.info(f"Received from TRANSLATION_WORKER: \"{translation_text}\"")
            else:
                transcription_text = result_data.get("text", "")
                self.logger.info(f"Received from STT_WORKER: \"{transcription_text}\"")

            # Only update last_sent for new segments or when we get the final result for a segment
            if segment_id > last_sent:
                self.redis_client.latest_segment_id_sent[client_id] = segment_id

            with self.gateway_service.client_lock:
                websocket = self.gateway_service.connected_clients.get(client_id)
            send_result_task = None
            utterance_end_task = None
            if websocket:
                try:
                    message = {
                        "type": "realtime",
                        "text": result_data.get("text", ""),
                        "translation": result_data.get("translation", ""),
                        "segment_id": result_data.get("segment_id", ""),
                        "processing_time": result_data.get("processing_time", 0.0)
                    }
                    result_text = (message['translation'] or message['text'])
                    self.logger.info(f"Sending \"{result_text}\" to client_id {client_id}")
                    send_result_task = asyncio.create_task(websocket.send(json.dumps(message)))
                    self.gateway_service.metrics["results_forwarded"] += 1
                    self.logger.debug(f"Successfully forwarded result to client {client_id}")

                    # Check if this is a final result and send utterance_end if so
                    is_final = result_data.get("is_final", False)
                    if isinstance(is_final, str):
                        is_final = is_final.lower() in ("true", "1", "yes")
                    elif not isinstance(is_final, bool):
                        is_final = bool(is_final)

                    # Only send utterance_end once per utterance:
                    # - If translation disabled: send on STT result (single layer)
                    # - If translation enabled: send only on translation result (double layer)
                    # This prevents duplicate utterance_end when translation is enabled
                    should_send_utterance_end = is_final and ((not translation_enabled) or is_translation_result)
                    
                    if should_send_utterance_end:
                        utterance_end_task = asyncio.create_task(self._send_utterance_end(websocket, client_id))
                        result_type = "translation" if is_translation_result else "transcription"
                        self.logger.info(f"Final {result_type} result received for client {client_id}, sending utterance_end")
                except ConnectionClosedError:
                    self.logger.info(f"Client {client_id} disconnected during result forwarding")
                    with self.gateway_service.client_lock:
                        self.gateway_service.connected_clients.pop(client_id, None)
                        self.gateway_service.metrics["clients_connected"] -= 1
                    await self.redis_client.delete_session(client_id)
                    await self.redis_client.unsubscribe_from_client_channel(client_id)
                except WebSocketException as e:
                    self.logger.warning(f"WebSocket error forwarding to client {client_id}: {e}")
                    self.gateway_service.metrics["errors"] += 1
                except Exception as e:
                    self.logger.error(f"Unexpected error forwarding to client {client_id}: {e}")
                    self.gateway_service.metrics["errors"] += 1
            else:
                self.logger.debug(f"No websocket found for client {client_id}")

            # Only unlock job when appropriate based on processing layers
            if should_unlock_job:
                self.redis_client.job_in_flight[client_id] = False
                mode = 'translation_enabled' if translation_enabled else 'disabled'
                layers = 'double_layer' if translation_enabled else 'single_layer'
                self.logger.debug(f"[EVENT=job_unlocked] [mode={mode}] [layers={layers}] [details=ready_for_next_job]")
            else:
                self.logger.debug(f"[EVENT=job_locked] [mode=translation_enabled] [layers=double_layer] [details=waiting_for_translation]")
            send_job_task = None
            # Only send next job if we've unlocked the current job
            if should_unlock_job and len(session.audio_buffer) > session.last_published_len:
                send_job_task = asyncio.create_task(self.gateway_service.publish_job_if_needed(client_id, session, is_final=False))
                # Avoid rewriting entire session blob; update only the changed field
                try:
                    # Encode strings to bytes for Redis
                    key = f"session:{client_id}".encode('utf-8')
                    value = str(session.last_published_len).encode('utf-8')
                    await self.redis_client.redis.hset(key, mapping={b"last_published_len": value})
                except Exception:
                    # Fall back silently; next full save will correct state
                    pass
            tasks = [t for t in [send_result_task, send_job_task, utterance_end_task] if t is not None]
            if tasks:
                await asyncio.gather(*tasks)
        else:
            self.logger.debug(f"Ignoring out-of-order segment {segment_id} for client {client_id} (last sent: {last_sent})")

    async def _cleanup_client(self, client_id, websocket):
        """Clean up client connection and resources"""
        self.logger.info(f"[GATEWAY-{self.gateway_service.instance_id}] Starting disconnect/cleanup for client {client_id}")
        try:
            if websocket is not None:
                try:
                    await websocket.close()
                    self.logger.info(f"[GATEWAY-{self.gateway_service.instance_id}] Explicitly closed websocket for client {client_id}")
                except Exception as e:
                    self.logger.error(f"[GATEWAY-{self.gateway_service.instance_id}] Error closing websocket for client {client_id}: {e}")
                # Wait for the close handshake to complete
                try:
                    await asyncio.wait_for(websocket.wait_closed(), timeout=1.0)
                except Exception:
                    pass
                # Force close the transport if still open
                try:
                    if hasattr(websocket, 'transport') and websocket.transport is not None:
                        websocket.transport.close()
                        self.logger.info(f"[GATEWAY-{self.gateway_service.instance_id}] Explicitly closed transport for client {client_id}")
                except Exception:
                    pass
        except Exception as e:
            self.logger.error(f"[GATEWAY-{self.gateway_service.instance_id}] Error closing websocket/transport for client {client_id}: {e}")
        try:
            with self.gateway_service.client_lock:
                self.gateway_service.connected_clients.pop(client_id, None)
                self.gateway_service.metrics["clients_connected"] -= 1
            # Clean up session and unsubscribe from result channel
            await self.redis_client.delete_session(client_id)
            await self.redis_client.unsubscribe_from_client_channel(client_id)
            self.logger.info(f"[GATEWAY-{self.gateway_service.instance_id}] Client {client_id} disconnected")
            self.logger.info(f"After disconnect: connected_clients={len(self.gateway_service.connected_clients)}, client_pubsubs={len(self.redis_client.client_pubsubs)}")
        except Exception as e:
            self.logger.error(f"[GATEWAY-{self.gateway_service.instance_id}] Error during cleanup for client {client_id}: {e}")
