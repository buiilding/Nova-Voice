import React from 'react';
import { motion } from 'motion/react';
import { Download, Play } from 'lucide-react';
import { Button } from './ui/button';
import { ImageWithFallback } from './figma/ImageWithFallback';

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-900/70 via-background to-slate-900/50" />
      
      {/* Floating Orbs */}
      <motion.div 
        className="absolute top-1/4 left-1/4 w-64 h-64 bg-primary/20 rounded-full blur-3xl"
        animate={{ 
          scale: [1, 1.2, 1],
          opacity: [0.3, 0.6, 0.3]
        }}
        transition={{ 
          duration: 4,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
      
      <motion.div 
        className="absolute bottom-1/3 right-1/3 w-48 h-48 bg-primary/15 rounded-full blur-3xl"
        animate={{ 
          scale: [1.2, 1, 1.2],
          opacity: [0.2, 0.5, 0.2]
        }}
        transition={{ 
          duration: 3,
          repeat: Infinity,
          ease: "easeInOut",
          delay: 1
        }}
      />

      {/* Content Container */}
      <div className="relative z-10 max-w-6xl mx-auto px-6 text-center">
        {/* Floating Microphone */}
        <motion.div 
          className="mb-8 inline-block"
          animate={{ 
            y: [-10, 10, -10],
            rotate: [0, 2, -2, 0]
          }}
          transition={{ 
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          <div className="relative w-24 h-24 p-0 bg-primary/10 backdrop-blur-md rounded-full border border-primary/30 shadow-2xl">
            <ImageWithFallback
              src="/favicon3.png"
              alt="Nova Voice Microphone"
              className="w-full h-full rounded-full object-contain drop-shadow-lg"
            />
            <div className="absolute inset-0 bg-primary/20 rounded-full animate-ping" />
          </div>
        </motion.div>

        {/* Main Heading */}
        <motion.h1 
          className="text-6xl md:text-8xl mb-6 bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-transparent"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3 }}
        >
          Type What You Say.
          <br />
          <span className="text-primary">See What You Speak</span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          className="text-xl md:text-2xl mb-12 text-muted-foreground max-w-3xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
        >
          Experience instant real-time voice typing and subtitle with Nova Voice.
          Transform speech into text with precision and speed.
        </motion.p>

        {/* Action Buttons */}
        <motion.div 
          className="flex flex-col sm:flex-row gap-6 justify-center items-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.9 }}
        >
          <Button
            size="lg"
            className="group relative px-8 py-4 bg-primary/20 backdrop-blur-md border border-primary/50 hover:border-primary hover:bg-primary/30 transition-all duration-300 shadow-2xl"
            onClick={() => window.location.href = 'https://downloads.nova-voice.com/Nova%20Voice%20Setup%200.1.0.exe'}
          >
            <Download className="w-5 h-5 mr-2" />
            Download for Windows
            <div className="absolute inset-0 bg-primary/20 rounded-lg blur-xl group-hover:blur-2xl transition-all duration-300" />
          </Button>
          
          <Button 
            variant="ghost" 
            size="lg"
            className="px-8 py-4 bg-transparent backdrop-blur-md border border-primary/30 hover:border-primary/50 hover:bg-primary/10 transition-all duration-300"
          >
            <Play className="w-5 h-5 mr-2" />
            Watch Demo
          </Button>
        </motion.div>

        {/* Wave Animation - Using transform to prevent layout shifts */}
        <motion.div
          className="mt-16 flex justify-center items-center space-x-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
        >
          {[...Array(5)].map((_, i) => (
            <motion.div
              key={i}
              className="w-1 h-16 bg-primary/60 rounded-full origin-bottom"
              animate={{
                scaleY: [0.3, 0.6, 1, 0.6, 0.3],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                delay: i * 0.1,
                ease: "easeInOut"
              }}
            />
          ))}
        </motion.div>
      </div>
    </section>
  );
}