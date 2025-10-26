"""
test_language_pairs.py - Comprehensive Test for All NLLB-200 Language Pairs

Tests all 42 language pairs (7 languages × 6 target languages each)
Measures translation quality, speed, and consistency.
"""

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import time
from datetime import datetime
import json
from typing import Dict, List, Tuple
import sys

# Language mapping
LANGUAGE_MAPPING = {
    "en": "eng_Latn",      # English
    "es": "spa_Latn",      # Spanish
    "fr": "fra_Latn",      # French
    "de": "deu_Latn",      # German
    "vi": "vie_Latn",      # Vietnamese
    "zh": "zho_Hans",      # Chinese Simplified
    "ja": "jpn_Jpan",      # Japanese
    "hi": "hin_Deva",      # Hindi
}

# Test sentences for each language
TEST_SENTENCES = {
    "en": "Hello, how are you today? I hope you're having a wonderful day.",
    "es": "Hola, ¿cómo estás hoy? Espero que tengas un día maravilloso.",
    "fr": "Bonjour, comment allez-vous aujourd'hui? J'espère que vous passez une merveilleuse journée.",
    "de": "Hallo, wie geht es dir heute? Ich hoffe, du hast einen wundervollen Tag.",
    "vi": "Xin chào, hôm nay bạn thế nào? Tôi hy vọng bạn đang có một ngày tuyệt vời.",
    "zh": "你好，你今天怎么样？我希望你度过美好的一天。",
    "ja": "こんにちは、今日はお元気ですか？素晴らしい一日をお過ごしください。",
    "hi": "नमस्ते, आज आप कैसे हैं? मुझे उम्मीद है कि आप एक अद्भुत दिन हैं।",
}

LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "vi": "Vietnamese",
    "zh": "Chinese",
    "ja": "Japanese",
    "hi": "Hindi",
}


class NLLBTester:
    def __init__(self, model_name="facebook/nllb-200-distilled-600M"):
        """Initialize the NLLB tester with model and tokenizer"""
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"🚀 Initializing NLLB-200 Tester")
        print(f"📦 Model: {model_name}")
        print(f"💻 Device: {self.device}")
        print("="*80)
        
        # Load model and tokenizer
        print("Loading model and tokenizer...")
        start_time = time.time()
        
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            low_cpu_mem_usage=True
        )
        self.model = self.model.to(self.device)
        self.model.eval()
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        load_time = time.time() - start_time
        print(f"✅ Model loaded in {load_time:.2f}s")
        
        if self.device == "cuda":
            print(f"🎮 GPU: {torch.cuda.get_device_name(0)}")
            print(f"💾 GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        
        print("="*80 + "\n")

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> Tuple[str, float]:
        """
        Translate text from source to target language
        
        Returns:
            Tuple of (translated_text, translation_time)
        """
        start_time = time.time()
        
        try:
            # Get NLLB codes
            src_code = LANGUAGE_MAPPING[src_lang]
            tgt_code = LANGUAGE_MAPPING[tgt_lang]
            
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            ).to(self.device)
            
            # Generate translation
            with torch.no_grad():
                translated_tokens = self.model.generate(
                    **inputs,
                    forced_bos_token_id=self.tokenizer.convert_tokens_to_ids(tgt_code),
                    max_length=200,
                    num_beams=5,
                    early_stopping=True
                )
            
            # Decode
            translation = self.tokenizer.batch_decode(
                translated_tokens,
                skip_special_tokens=True
            )[0]
            
            # Clean up
            del inputs
            del translated_tokens
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            translation_time = time.time() - start_time
            return translation, translation_time
            
        except Exception as e:
            print(f"❌ Error translating {src_lang}->{tgt_lang}: {e}")
            return f"ERROR: {str(e)}", 0.0

    def test_all_pairs(self) -> Dict:
        """Test all 42 language pairs"""
        all_languages = list(LANGUAGE_MAPPING.keys())
        total_pairs = len(all_languages) * (len(all_languages) - 1)
        
        print(f"🧪 Testing {total_pairs} language pairs")
        print(f"📝 Languages: {', '.join([LANGUAGE_NAMES[l] for l in all_languages])}")
        print("="*80 + "\n")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "model": self.model_name,
            "device": self.device,
            "total_pairs": total_pairs,
            "translations": [],
            "statistics": {
                "total_time": 0.0,
                "avg_time_per_translation": 0.0,
                "fastest_pair": None,
                "slowest_pair": None,
                "success_count": 0,
                "error_count": 0
            }
        }
        
        pair_count = 0
        total_time = 0.0
        translation_times = []
        
        # Test each source language
        for src_lang in all_languages:
            src_text = TEST_SENTENCES[src_lang]
            src_name = LANGUAGE_NAMES[src_lang]
            
            print(f"\n{'='*80}")
            print(f"📤 SOURCE: {src_name} ({src_lang})")
            print(f"📝 Text: {src_text}")
            print(f"{'='*80}")
            
            # Translate to all other languages
            for tgt_lang in all_languages:
                if src_lang == tgt_lang:
                    continue  # Skip same language
                
                pair_count += 1
                tgt_name = LANGUAGE_NAMES[tgt_lang]
                
                print(f"\n[{pair_count}/{total_pairs}] {src_name} → {tgt_name} ({src_lang}→{tgt_lang})")
                
                # Perform translation
                translation, trans_time = self.translate(src_text, src_lang, tgt_lang)
                total_time += trans_time
                translation_times.append((trans_time, src_lang, tgt_lang))
                
                # Display result
                if not translation.startswith("ERROR"):
                    print(f"✅ Translation: {translation}")
                    print(f"⏱️  Time: {trans_time:.3f}s")
                    results["statistics"]["success_count"] += 1
                else:
                    print(f"❌ {translation}")
                    results["statistics"]["error_count"] += 1
                
                # Store result
                results["translations"].append({
                    "pair_number": pair_count,
                    "source_lang": src_lang,
                    "target_lang": tgt_lang,
                    "source_lang_name": src_name,
                    "target_lang_name": tgt_name,
                    "source_text": src_text,
                    "translation": translation,
                    "translation_time": trans_time,
                    "success": not translation.startswith("ERROR")
                })
        
        # Calculate statistics
        results["statistics"]["total_time"] = total_time
        results["statistics"]["avg_time_per_translation"] = total_time / total_pairs
        
        # Find fastest and slowest pairs
        translation_times.sort()
        fastest = translation_times[0]
        slowest = translation_times[-1]
        
        results["statistics"]["fastest_pair"] = {
            "time": fastest[0],
            "source": fastest[1],
            "target": fastest[2],
            "pair": f"{LANGUAGE_NAMES[fastest[1]]} → {LANGUAGE_NAMES[fastest[2]]}"
        }
        
        results["statistics"]["slowest_pair"] = {
            "time": slowest[0],
            "source": slowest[1],
            "target": slowest[2],
            "pair": f"{LANGUAGE_NAMES[slowest[1]]} → {LANGUAGE_NAMES[slowest[2]]}"
        }
        
        return results

    def print_summary(self, results: Dict):
        """Print test summary"""
        stats = results["statistics"]
        
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        print(f"✅ Successful translations: {stats['success_count']}/{results['total_pairs']}")
        print(f"❌ Failed translations: {stats['error_count']}/{results['total_pairs']}")
        print(f"⏱️  Total time: {stats['total_time']:.2f}s")
        print(f"⚡ Average time per translation: {stats['avg_time_per_translation']:.3f}s")
        
        if stats['fastest_pair']:
            print(f"\n🚀 Fastest pair: {stats['fastest_pair']['pair']} ({stats['fastest_pair']['time']:.3f}s)")
        
        if stats['slowest_pair']:
            print(f"🐌 Slowest pair: {stats['slowest_pair']['pair']} ({stats['slowest_pair']['time']:.3f}s)")
        
        print("="*80)

    def save_results(self, results: Dict, filename: str = "translation_test_results.json"):
        """Save results to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Results saved to {filename}")

    def print_language_matrix(self, results: Dict):
        """Print a matrix showing which language pairs were tested"""
        print("\n" + "="*80)
        print("🗺️  TRANSLATION MATRIX")
        print("="*80)
        
        languages = list(LANGUAGE_MAPPING.keys())
        
        # Print header
        print(f"{'':>6}", end="")
        for lang in languages:
            print(f"{lang:>8}", end="")
        print()
        
        # Print rows
        for src_lang in languages:
            print(f"{src_lang:>6}", end="")
            for tgt_lang in languages:
                if src_lang == tgt_lang:
                    print(f"{'—':>8}", end="")
                else:
                    # Find translation result
                    translation = next(
                        (t for t in results["translations"] 
                         if t["source_lang"] == src_lang and t["target_lang"] == tgt_lang),
                        None
                    )
                    if translation and translation["success"]:
                        print(f"{'✓':>8}", end="")
                    else:
                        print(f"{'✗':>8}", end="")
            print()
        
        print("\n✓ = Successful translation")
        print("✗ = Failed translation")
        print("— = Same language (skipped)")
        print("="*80)


def main():
    """Main test function"""
    print("\n" + "="*80)
    print("🌍 NLLB-200 Language Pair Tester")
    print("="*80)
    print(f"Testing {len(LANGUAGE_MAPPING)} languages with {len(LANGUAGE_MAPPING) * (len(LANGUAGE_MAPPING) - 1)} translation pairs")
    print("="*80 + "\n")
    
    # Initialize tester
    tester = NLLBTester(model_name="facebook/nllb-200-distilled-600M")
    
    # Run tests
    print("🏃 Starting translation tests...\n")
    results = tester.test_all_pairs()
    
    # Print summary
    tester.print_summary(results)
    
    # Print matrix
    tester.print_language_matrix(results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"nllb_test_results_{timestamp}.json"
    tester.save_results(results, filename)
    
    print("\n✨ Testing complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)