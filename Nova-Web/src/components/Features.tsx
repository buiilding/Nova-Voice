import { motion } from 'motion/react';
import { Mic, Globe, Type, Zap } from 'lucide-react';

const features = [
  {
    icon: Type,
    title: "Real-time Voice Typing",
    description: "Convert speech to text instantly with industry-leading accuracy and lightning-fast processing."
  },
  {
    icon: Globe,
    title: "Multi-language Translation", 
    description: "Support for 100+ languages with real-time translation capabilities for global communication."
  },
  {
    icon: Mic,
    title: "Live Subtitles",
    description: "Generate live subtitles for meetings, lectures, and conversations with perfect synchronization."
  },
  {
    icon: Zap,
    title: "Lightning Fast",
    description: "Optimized desktop performance with minimal latency and maximum reliability for professionals."
  }
];

export function Features() {
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
            Powerful Features
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Experience the future of voice technology with advanced features designed for modern workflows.
          </p>
        </motion.div>

        {/* Feature Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              className="group relative p-6 bg-background/20 backdrop-blur-md rounded-xl border border-primary/20 hover:border-primary/50 transition-all duration-500 hover:bg-background/30"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              viewport={{ once: true }}
              whileHover={{ y: -5 }}
            >
              {/* Glow Effect */}
              <div className="absolute inset-0 bg-primary/5 rounded-xl blur-xl group-hover:bg-primary/10 transition-all duration-500" />
              
              {/* Icon */}
              <div className="relative mb-4 p-3 bg-primary/10 rounded-lg w-fit border border-primary/30">
                <feature.icon className="w-6 h-6 text-primary" />
              </div>
              
              {/* Content */}
              <div className="relative">
                <h3 className="mb-3 text-foreground group-hover:text-primary transition-colors duration-300">
                  {feature.title}
                </h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>

              {/* Border Glow */}
              <div className="absolute inset-0 border border-primary/0 group-hover:border-primary/30 rounded-xl transition-all duration-500" />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}