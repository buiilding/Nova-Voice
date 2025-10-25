import { motion } from 'motion/react';
import { Github, Twitter, Mail, Heart } from 'lucide-react';

export function Footer() {
  return (
    <footer className="py-16 px-6 border-t border-primary/20">
      <div className="max-w-6xl mx-auto">
        {/* Main Footer Content */}
        <motion.div 
          className="text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
        >
          {/* Logo */}
          <div className="mb-6">
            <h3 className="text-2xl bg-gradient-to-r from-foreground to-primary bg-clip-text text-transparent">
              Nova Voice
            </h3>
            <p className="text-muted-foreground mt-2">
              The future of voice technology
            </p>
          </div>

          {/* Social Links */}
          <div className="flex justify-center space-x-6 mb-8">
            {[
              { icon: Github, href: "#", label: "GitHub" },
              { icon: Twitter, href: "#", label: "Twitter" },
              { icon: Mail, href: "#", label: "Email" }
            ].map((social, index) => (
              <motion.a
                key={index}
                href={social.href}
                className="p-3 bg-background/20 backdrop-blur-sm rounded-lg border border-primary/20 hover:border-primary/50 hover:bg-primary/10 transition-all duration-300 group"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                aria-label={social.label}
              >
                <social.icon className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors duration-300" />
              </motion.a>
            ))}
          </div>

          {/* Navigation Links */}
          <motion.div 
            className="flex flex-wrap justify-center gap-8 mb-8 text-sm"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            viewport={{ once: true }}
          >
            {["Privacy Policy", "Terms of Service", "Support", "Documentation", "About"].map((link, index) => (
              <a
                key={index}
                href="#"
                className="text-muted-foreground hover:text-primary transition-colors duration-300 hover:underline underline-offset-4"
              >
                {link}
              </a>
            ))}
          </motion.div>
        </motion.div>

        {/* Bottom Bar */}
        <motion.div 
          className="pt-8 border-t border-primary/10 text-center"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          viewport={{ once: true }}
        >
          <p className="text-xs text-muted-foreground flex items-center justify-center gap-2">
            Made with <Heart className="w-3 h-3 text-primary" /> by the Nova Voice team
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            © 2025 Nova Voice. All rights reserved.
          </p>
        </motion.div>
      </div>
    </footer>
  );
}