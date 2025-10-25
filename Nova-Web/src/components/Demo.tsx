import { motion } from 'motion/react';
import { ImageWithFallback } from './figma/ImageWithFallback';

export function Demo() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section Header */}
        <motion.div 
          className="text-center mb-16"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
        >
          <h2 className="text-4xl md:text-5xl mb-4 bg-gradient-to-r from-foreground to-primary bg-clip-text text-transparent">
            See Nova Voice in Action
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Watch how speech transforms into text with precision and speed, enabling seamless communication across languages.
          </p>
        </motion.div>

        {/* Demo Container */}
        <motion.div 
          className="relative max-w-5xl mx-auto"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          viewport={{ once: true }}
        >
          {/* Glass Panel */}
          <div className="relative p-6 md:p-8 bg-background/10 backdrop-blur-md rounded-2xl border border-primary/30 shadow-2xl">
            {/* Glow Effect */}
            <div className="absolute inset-0 bg-primary/5 rounded-2xl blur-2xl" />
            
            {/* Demo Video Container - 16:9 Aspect Ratio */}
            <div className="relative w-full aspect-video rounded-xl overflow-hidden border border-primary/20 bg-slate-900/50">
              <ImageWithFallback
                src="https://images.unsplash.com/photo-1575388902449-6bca946ad549?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx2b2ljZSUyMHR5cGluZyUyMGFwcGxpY2F0aW9uJTIwc2NyZWVuJTIwaW50ZXJmYWNlfGVufDF8fHx8MTc1OTE5NjI3NHww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                alt="Nova Voice application interface demonstration"
                className="w-full h-full object-cover rounded-xl"
              />
              
              {/* Overlay with reflection effect */}
              <div className="absolute inset-0 bg-gradient-to-tr from-primary/10 via-transparent to-primary/5 rounded-xl" />
              
              {/* Play Button Overlay */}
              <div className="absolute inset-0 flex items-center justify-center">
                <motion.button 
                  className="w-20 h-20 bg-primary/20 backdrop-blur-md rounded-full border border-primary/40 flex items-center justify-center group hover:bg-primary/30 transition-all duration-300"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <div className="w-0 h-0 border-l-8 border-l-primary border-t-6 border-t-transparent border-b-6 border-b-transparent ml-1" />
                  <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl group-hover:blur-2xl transition-all duration-300" />
                </motion.button>
              </div>
            </div>

            {/* Demo Steps */}
            <div className="mt-6 md:mt-8 grid md:grid-cols-3 gap-4 md:gap-6">
              <motion.div 
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                viewport={{ once: true }}
              >
                <div className="mb-3 w-8 h-8 mx-auto bg-primary/20 rounded-full flex items-center justify-center border border-primary/40">
                  <span className="text-primary">1</span>
                </div>
                <h4 className="mb-2 text-primary">Speak Naturally</h4>
                <p className="text-sm text-muted-foreground">
                  Talk at your normal pace and tone
                </p>
              </motion.div>

              <motion.div 
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.5 }}
                viewport={{ once: true }}
              >
                <div className="mb-3 w-8 h-8 mx-auto bg-primary/20 rounded-full flex items-center justify-center border border-primary/40">
                  <span className="text-primary">2</span>
                </div>
                <h4 className="mb-2 text-primary">Real-time Processing</h4>
                <p className="text-sm text-muted-foreground">
                  Watch text appear instantly as you speak
                </p>
              </motion.div>

              <motion.div 
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.6 }}
                viewport={{ once: true }}
              >
                <div className="mb-3 w-8 h-8 mx-auto bg-primary/20 rounded-full flex items-center justify-center border border-primary/40">
                  <span className="text-primary">3</span>
                </div>
                <h4 className="mb-2 text-primary">Perfect Translation</h4>
                <p className="text-sm text-muted-foreground">
                  Instantly translate to any language
                </p>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}