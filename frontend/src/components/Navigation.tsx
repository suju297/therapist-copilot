import { useState } from "react";
import { 
  User, 
  Shield, 
  Menu,
  X,
  MessageCircle,
  AlertTriangle,
  Home,
  ChevronLeft,
  ChevronRight
} from "lucide-react";

interface NavigationProps {
  currentPage: string;
  onPageChange: (page: string) => void;
  patientName?: string;
  riskLevel?: "none" | "high";
  onCollapseChange?: (collapsed: boolean) => void;
}

export default function Navigation({ 
  currentPage, 
  onPageChange, 
  patientName = "No Patient Selected",
  riskLevel = "none",
  onCollapseChange
}: NavigationProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(true);

  const toggleCollapse = () => {
    const newCollapsed = !isCollapsed;
    setIsCollapsed(newCollapsed);
    onCollapseChange?.(newCollapsed);
  };

  const navigationItems = [
    {
      id: "dashboard",
      label: "Live Session",
      icon: MessageCircle,
      description: "Real-time transcription & monitoring"
    },
    {
      id: "patient-overview",
      label: "Patient Overview",
      icon: User,
      description: "Demographics, history & assessments"
    },
    {
      id: "safety",
      label: "Safety & Crisis",
      icon: Shield,
      description: "Risk management & protocols"
    }
  ];

  return (
    <>
      {/* Desktop Toggle Button */}
      <button
        onClick={toggleCollapse}
        className="hidden lg:block fixed top-4 left-4 z-50 bg-white p-2 rounded-lg shadow-lg hover:bg-gray-50 transition-colors"
      >
        {isCollapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
      </button>

      {/* Mobile menu button */}
      <button
        onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 bg-white p-2 rounded-lg shadow-lg"
      >
        {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
      </button>

      {/* Sidebar Navigation */}
      <nav className={`
        fixed left-0 top-0 h-full bg-white shadow-xl border-r border-gray-200 z-40
        transform transition-all duration-300 ease-in-out pt-16
        ${isCollapsed ? 'w-16' : 'w-80'}
        ${isMobileMenuOpen ? 'translate-x-0 w-80' : 'lg:translate-x-0 -translate-x-full lg:block'}
      `}>
        {/* Header */}
        <div className={`p-6 border-b border-gray-200 ${isCollapsed ? 'hidden' : 'block'}`}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <Home className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Therapist Co-Pilot</h1>
              <p className="text-sm text-gray-500">AI-Powered Session Assistant</p>
            </div>
          </div>
          
          {/* Current Patient */}
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-600">Current Patient</span>
              {riskLevel === "high" && (
                <AlertTriangle className="h-4 w-4 text-red-500" />
              )}
            </div>
            <p className="font-semibold text-gray-900 truncate">{patientName}</p>
            <div className="flex items-center gap-2 mt-2">
              <div className={`w-2 h-2 rounded-full ${
                riskLevel === "high" ? "bg-red-500" : "bg-green-500"
              }`}></div>
              <span className="text-xs text-gray-500">
                {riskLevel === "high" ? "High Risk - Monitor Closely" : "Session Active"}
              </span>
            </div>
          </div>
        </div>

        {/* Collapsed Header */}
        <div className={`p-4 border-b border-gray-200 ${isCollapsed ? 'block' : 'hidden'}`}>
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center mx-auto">
            <Home className="h-4 w-4 text-white" />
          </div>
          {riskLevel === "high" && (
            <AlertTriangle className="h-4 w-4 text-red-500 mx-auto mt-2" />
          )}
        </div>

        {/* Navigation Items */}
        <div className="p-4 space-y-2 overflow-y-auto h-full">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPage === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => {
                  onPageChange(item.id);
                  setIsMobileMenuOpen(false);
                }}
                className={`
                  w-full text-left rounded-lg transition-all duration-200 relative group
                  ${isActive 
                    ? 'bg-blue-50 border border-blue-200 text-blue-700 shadow-sm' 
                    : 'hover:bg-gray-50 text-gray-700 hover:text-gray-900'
                  }
                  ${isCollapsed ? 'p-2 flex justify-center' : 'p-3'}
                `}
              >
                {isCollapsed ? (
                  <>
                    <Icon className={`h-5 w-5 ${
                      isActive ? 'text-blue-600' : 'text-gray-500'
                    }`} />
                    {/* Tooltip on hover */}
                    <div className="absolute left-16 top-1/2 -translate-y-1/2 bg-gray-800 text-white px-2 py-1 rounded text-sm opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                      {item.label}
                    </div>
                  </>
                ) : (
                  <div className="flex items-start gap-3">
                    <Icon className={`h-5 w-5 mt-0.5 ${
                      isActive ? 'text-blue-600' : 'text-gray-500'
                    }`} />
                    <div>
                      <p className="font-medium">{item.label}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{item.description}</p>
                    </div>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Mobile overlay */}
      {isMobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}
    </>
  );
}
