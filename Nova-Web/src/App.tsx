import { Hero } from './components/Hero';
import { Features } from './components/Features';
import { Demo } from './components/Demo';
import { DownloadCTA } from './components/DownloadCTA';
import { Footer } from './components/Footer';

export default function App() {
  return (
    <div className="min-h-screen bg-background text-foreground dark">
      {/* Background Elements */}
      <div className="fixed inset-0 bg-gradient-to-br from-background via-slate-900/20 to-background pointer-events-none" />
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_30%_20%,theme(colors.primary/10),transparent_50%)] pointer-events-none" />
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_70%_80%,theme(colors.primary/5),transparent_50%)] pointer-events-none" />
      
      {/* Main Content */}
      <div className="relative z-10">
        <Hero />
        <Features />
        <Demo />
        <DownloadCTA />
        <Footer />
      </div>
    </div>
  );
}