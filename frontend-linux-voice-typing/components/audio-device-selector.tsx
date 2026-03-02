"use client"

import { useState, useEffect } from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Mic, Volume2, ChevronDown } from "lucide-react"
import { audioDeviceManager, AudioDevice, AudioDeviceCategory } from "@/lib/audio-devices"

interface AudioDeviceSelectorProps {
  value?: string
  onValueChange: (deviceId: string) => void
  placeholder?: string
  className?: string
  disabled?: boolean
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function AudioDeviceSelector({
  value,
  onValueChange,
  placeholder = "Select audio device",
  className = "",
  disabled = false,
  open: controlledOpen,
  onOpenChange: controlledOnOpenChange
}: AudioDeviceSelectorProps) {
  const [devices, setDevices] = useState<AudioDeviceCategory[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [internalOpen, setInternalOpen] = useState(false)
  const [showSystemAudioSelector, setShowSystemAudioSelector] = useState(false)
  
  // Use controlled state if provided, otherwise use internal state
  const open = controlledOpen !== undefined ? controlledOpen : internalOpen
  const setOpen = (newOpen: boolean) => {
    if (controlledOnOpenChange) {
      controlledOnOpenChange(newOpen)
    } else {
      setInternalOpen(newOpen)
    }
  }

  useEffect(() => {
    loadDevices()
    
    // Listen for device changes
    const handleDeviceChange = () => {
      loadDevices()
    }
    
    navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange)
    
    return () => {
      navigator.mediaDevices.removeEventListener('devicechange', handleDeviceChange)
    }
  }, [])

  const loadDevices = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      await audioDeviceManager.enumerateDevices()
      const categorizedDevices = audioDeviceManager.getCategorizedDevices()
      setDevices(categorizedDevices)
      
      // Set default value if none selected
      if (!value && categorizedDevices.length > 0) {
        // Prefer system audio if available, otherwise use first input device
        const systemAudioDevice = categorizedDevices
          .find(cat => cat.type === 'output')
          ?.devices[0]
        
        const firstInputDevice = categorizedDevices
          .find(cat => cat.type === 'input')
          ?.devices[0]
        
        if (systemAudioDevice) {
          onValueChange(systemAudioDevice.deviceId)
        } else if (firstInputDevice) {
          onValueChange(firstInputDevice.deviceId)
        }
      }
    } catch (err) {
      setError('Failed to load audio devices')
      console.error('Error loading audio devices:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getDeviceIcon = (type: 'input' | 'output') => {
    return type === 'input' ? (
      <Mic className="w-3 h-3 mr-2 text-slate-400" />
    ) : (
      <Volume2 className="w-3 h-3 mr-2 text-slate-400" />
    )
  }

  const getSelectedDeviceLabel = () => {
    if (!value) return placeholder
    
    for (const category of devices) {
      const device = category.devices.find(d => d.deviceId === value)
      if (device) {
        if (category.type === 'output') {
          return 'System Audio'
        }
        return device.label
      }
    }
    
    return placeholder
  }



  if (error) {
    return (
      <div className={`flex items-center justify-between p-2 bg-red-900/20 border border-red-700/30 rounded-lg text-red-300 text-sm ${className}`}>
        <span>{error}</span>
        <button
          onClick={loadDevices}
          className="text-red-400 hover:text-red-300 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <Select
      value={value}
      onValueChange={onValueChange}
      open={open}
      onOpenChange={setOpen}
      disabled={disabled || isLoading}
    >
      <SelectTrigger className={`w-full h-10 bg-slate-800/50 border border-slate-600 text-white ${className}`}>
        <SelectValue placeholder={isLoading ? "Loading devices..." : placeholder}>
          {getSelectedDeviceLabel()}
        </SelectValue>
      </SelectTrigger>
      
      <SelectContent className="bg-slate-800 border border-slate-600 max-h-80">
        {isLoading ? (
          <div className="p-4 text-center text-slate-400">
            Loading audio devices...
          </div>
        ) : devices.length === 0 ? (
          <div className="p-4 text-center text-slate-400">
            No audio devices found
          </div>
        ) : (
          <>
            {devices.map((category, categoryIndex) => (
              <div key={category.type}>
                {/* Category Header */}
                <div className="px-3 py-2 text-xs font-medium text-slate-500 uppercase tracking-wider border-b border-slate-700/50">
                  {category.label}
                </div>
                
                {/* Devices in this category */}
                {category.devices.map((device, deviceIndex) => (
                  <SelectItem
                    key={device.deviceId}
                    value={device.deviceId}
                    className="text-white hover:bg-slate-700 focus:bg-slate-700"
                  >
                    <div className="flex items-center w-full">
                      {getDeviceIcon(category.type)}
                      <span className="truncate">
                        {category.type === 'output' ? 'Capture System Audio' : device.label}
                      </span>
                      {category.type === 'output' && window.electronAPI && (
                        <span className="ml-2 text-xs text-green-400">(Direct)</span>
                      )}
                    </div>
                  </SelectItem>
                ))}
                
                {/* Add separator between categories */}
                {categoryIndex < devices.length - 1 && (
                  <div className="h-px bg-slate-700/50 my-1" />
                )}
              </div>
            ))}
            

          </>
        )}
      </SelectContent>
    </Select>
  )
}
