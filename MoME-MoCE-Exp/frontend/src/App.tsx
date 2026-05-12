import { useState } from "react";
import Header from "./components/Header";
import HeroStatus from "./components/HeroStatus";
import Dashboard from "./components/Dashboard";
import MobilePreview from "./components/MobilePreview";
import MemorySection from "./components/MemorySection";
import ContextSection from "./components/ContextSection";
import SourcesSection from "./components/SourcesSection";
import RecallSection from "./components/RecallSection";
import HowItWorks from "./components/HowItWorks";
import DeveloperHooks from "./components/DeveloperHooks";
import AccessSection from "./components/AccessSection";
import Footer from "./components/Footer";
import { useAlexandriaHooks } from "./hooks/useAlexandriaHooks";

export default function App() {
  const [activeNav, setActiveNav] = useState("Memory");
  const [mode, setMode] = useState<"simple" | "advanced">("advanced");
  const alexandria = useAlexandriaHooks();

  return (
    <div className="min-h-screen bg-ivory flex flex-col">
      <Header
        activeNav={activeNav}
        setActiveNav={setActiveNav}
        searchQuery={alexandria.query}
        setSearchQuery={alexandria.setQuery}
        onSearchSubmit={alexandria.runPacket}
        serviceLabel={alexandria.data.serviceLabel}
      />

      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-6 space-y-10">
        {/* Top dashboard area */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left column */}
          <div className="lg:col-span-3">
            <HeroStatus data={alexandria.data} />
          </div>

          {/* Center dashboard */}
          <div className="lg:col-span-9 xl:col-span-6">
            <Dashboard
              mode={mode}
              setMode={setMode}
              data={alexandria.data}
              query={alexandria.query}
              setQuery={alexandria.setQuery}
              runPacket={alexandria.runPacket}
              isRunning={alexandria.isRunning}
            />
          </div>

          {/* Right mobile preview */}
          <div className="hidden xl:block xl:col-span-3">
            <MobilePreview data={alexandria.data} sendFeedback={alexandria.sendFeedback} />
          </div>
        </div>

        {/* Advanced sections */}
        <div className="space-y-10">
          <MemorySection rows={alexandria.data.memoryFacts} />
          <ContextSection data={alexandria.data.contextPacket} metrics={alexandria.data.metrics} />
          <SourcesSection rows={alexandria.data.sourceTableRows} />
          <RecallSection />
          <HowItWorks />
          <DeveloperHooks
            apiBase={alexandria.data.apiBase}
            endpoints={alexandria.data.apiEndpoints}
            request={alexandria.data.apiRequest}
            preview={alexandria.data.apiPreview}
            connection={alexandria.data.connection}
          />
          <AccessSection />
        </div>
      </main>

      <Footer />
    </div>
  );
}
