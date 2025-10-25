import { motion } from 'motion/react';
import { Download, CheckCircle, Shield, Zap } from 'lucide-react';
import { Button } from './ui/button';

export function DownloadCTA() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        {/* Main CTA Panel */}
        <motion.div 
          className="relative p-12 bg-background/10 backdrop-blur-md rounded-3xl border border-primary/40 shadow-2xl text-center"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
        >
          {/* Animated Glow */}
          <div className="absolute inset-0 bg-primary/10 rounded-3xl blur-3xl animate-pulse" />
          
          {/* Content */}
          <div className="relative">
            <motion.h2 
              className="text-4xl md:text-5xl mb-6 bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-transparent"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              viewport={{ once: true }}
            >
              Ready to Speak the Future?
            </motion.h2>
            
            <motion.p 
              className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              viewport={{ once: true }}
            >
              Download Nova Voice for Windows and transform how you interact with technology through the power of voice.
            </motion.p>

            {/* Download Button */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              viewport={{ once: true }}
            >
              <Button 
                size="lg" 
                className="group relative px-12 py-6 bg-primary hover:bg-primary/80 text-primary-foreground transition-all duration-300 shadow-2xl hover:shadow-primary/50 text-lg"
                onClick={() => window.location.href = 'https://downloads.nova-voice.com/Nova%20Voice%20Setup%200.1.0.exe'}
              >
                <Download className="w-6 h-6 mr-3" />
                Download Nova Voice
                
                {/* Button Glow Effect */}
                <div className="absolute inset-0 bg-primary/40 rounded-lg blur-xl group-hover:blur-2xl transition-all duration-300 -z-10" />
              </Button>
            </motion.div>

            {/* Features List */}
            <motion.div 
              className="mt-12 grid md:grid-cols-3 gap-6 text-left"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.5 }}
              viewport={{ once: true }}
            >
              <div className="flex items-center space-x-3">
                <CheckCircle className="w-5 h-5 text-primary flex-shrink-0" />
                <span className="text-sm text-muted-foreground">Free to download</span>
              </div>
              <div className="flex items-center space-x-3">
                <Shield className="w-5 h-5 text-primary flex-shrink-0" />
                <span className="text-sm text-muted-foreground">Privacy focused</span>
              </div>
              <div className="flex items-center space-x-3">
                <Zap className="w-5 h-5 text-primary flex-shrink-0" />
                <span className="text-sm text-muted-foreground">Instant setup</span>
              </div>
            </motion.div>

            {/* System Requirements */}
            <motion.div 
              className="mt-8 p-4 bg-background/20 backdrop-blur-sm rounded-xl border border-primary/20"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.6 }}
              viewport={{ once: true }}
            >
              <p className="text-xs text-muted-foreground">
                <strong className="text-primary">System Requirements:</strong> Windows 10/11, 4GB RAM, Microphone access
              </p>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}