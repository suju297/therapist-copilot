// src/pages/AnalyticsDashboard.tsx
import { BarChart3, TrendingUp, TrendingDown, Clock, Target, Shield, Award } from "lucide-react";

interface AnalyticsData {
  outcomeMetrics: {
    phq9Trend: Array<{ date: string; score: number }>;
    gad7Trend: Array<{ date: string; score: number }>;
    homeworkCompletion: number;
    sessionAttendance: number;
  };
  clinicianEfficiency: {
    noteTimeReduction: number;
    billingAccuracy: number;
    documentationSpeed: string;
  };
  riskManagement: {
    riskEpisodes: number;
    averageResponseTime: string;
    safetyPlanActivations: number;
  };
  qualityMetrics: {
    clientSatisfaction: number;
    treatmentGoalAchievement: number;
    sessionUtilization: number;
  };
}

export default function AnalyticsDashboard() {
  const analyticsData: AnalyticsData = {
    outcomeMetrics: {
      phq9Trend: [
        { date: "2023-10-01", score: 19 },
        { date: "2023-11-01", score: 16 },
        { date: "2023-12-01", score: 14 },
        { date: "2024-01-01", score: 12 },
        { date: "2024-01-15", score: 14 }
      ],
      gad7Trend: [
        { date: "2023-10-01", score: 15 },
        { date: "2023-11-01", score: 13 },
        { date: "2023-12-01", score: 11 },
        { date: "2024-01-01", score: 9 },
        { date: "2024-01-15", score: 11 }
      ],
      homeworkCompletion: 78,
      sessionAttendance: 92
    },
    clinicianEfficiency: {
      noteTimeReduction: 67,
      billingAccuracy: 98,
      documentationSpeed: "8 minutes average"
    },
    riskManagement: {
      riskEpisodes: 2,
      averageResponseTime: "< 30 seconds",
      safetyPlanActivations: 1
    },
    qualityMetrics: {
      clientSatisfaction: 4.7,
      treatmentGoalAchievement: 85,
      sessionUtilization: 94
    }
  };

  const MetricCard = ({ 
    title, 
    value, 
    trend, 
    icon: Icon, 
    color = "blue",
    subtitle 
  }: {
    title: string;
    value: string | number;
    trend?: "up" | "down" | "stable";
    icon: any;
    color?: string;
    subtitle?: string;
  }) => {
    const colorClasses = {
      blue: "text-blue-600 bg-blue-50",
      green: "text-green-600 bg-green-50",
      red: "text-red-600 bg-red-50",
      purple: "text-purple-600 bg-purple-50",
      orange: "text-orange-600 bg-orange-50"
    };

    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-lg ${colorClasses[color as keyof typeof colorClasses]}`}>
            <Icon className="h-6 w-6" />
          </div>
          {trend && (
            <div className={`flex items-center gap-1 text-sm ${
              trend === "up" ? "text-green-600" : trend === "down" ? "text-red-600" : "text-gray-600"
            }`}>
              {trend === "up" && <TrendingUp className="h-4 w-4" />}
              {trend === "down" && <TrendingDown className="h-4 w-4" />}
              {trend === "stable" && <div className="w-4 h-4 border-t-2 border-gray-400"></div>}
            </div>
          )}
        </div>
        <h3 className="text-sm font-medium text-gray-600 mb-1">{title}</h3>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
      </div>
    );
  };

  const TrendChart = ({ 
    data, 
    title, 
    color = "blue" 
  }: { 
    data: Array<{ date: string; score: number }>; 
    title: string;
    color?: string;
  }) => {
    const maxScore = Math.max(...data.map(d => d.score));
    const minScore = Math.min(...data.map(d => d.score));
    
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="h-48 flex items-end justify-between gap-2">
          {data.map((point, index) => {
            const height = ((point.score - minScore) / (maxScore - minScore)) * 100;
            return (
              <div key={index} className="flex flex-col items-center flex-1">
                <div className="text-xs text-gray-600 mb-1">{point.score}</div>
                <div 
                  className={`w-full bg-${color}-500 rounded-t transition-all duration-500`}
                  style={{ height: `${Math.max(height, 10)}%` }}
                ></div>
                <div className="text-xs text-gray-500 mt-2 rotate-45 origin-left">
                  {new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Analytics & Outcomes</h1>
        <p className="text-gray-600">Track patient progress, clinician efficiency, and system performance</p>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Homework Completion"
          value={`${analyticsData.outcomeMetrics.homeworkCompletion}%`}
          trend="up"
          icon={Target}
          color="green"
          subtitle="Last 30 days"
        />
        <MetricCard
          title="Session Attendance"
          value={`${analyticsData.outcomeMetrics.sessionAttendance}%`}
          trend="stable"
          icon={Award}
          color="blue"
          subtitle="Last 3 months"
        />
        <MetricCard
          title="Note Time Saved"
          value={`${analyticsData.clinicianEfficiency.noteTimeReduction}%`}
          trend="up"
          icon={Clock}
          color="purple"
          subtitle="vs manual entry"
        />
        <MetricCard
          title="Risk Response Time"
          value={analyticsData.riskManagement.averageResponseTime}
          trend="down"
          icon={Shield}
          color="orange"
          subtitle="Average detection to alert"
        />
      </div>

      {/* Assessment Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TrendChart
          data={analyticsData.outcomeMetrics.phq9Trend}
          title="PHQ-9 Depression Scores"
          color="blue"
        />
        <TrendChart
          data={analyticsData.outcomeMetrics.gad7Trend}
          title="GAD-7 Anxiety Scores"
          color="green"
        />
      </div>

      {/* Detailed Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Clinician Efficiency */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Clock className="h-5 w-5 text-purple-600" />
            Clinician Efficiency
          </h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Documentation Speed</span>
              <span className="font-semibold text-gray-900">{analyticsData.clinicianEfficiency.documentationSpeed}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Billing Accuracy</span>
              <span className="font-semibold text-green-600">{analyticsData.clinicianEfficiency.billingAccuracy}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Time Reduction</span>
              <span className="font-semibold text-purple-600">{analyticsData.clinicianEfficiency.noteTimeReduction}%</span>
            </div>
          </div>
        </div>

        {/* Quality Metrics */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Award className="h-5 w-5 text-green-600" />
            Quality Metrics
          </h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Client Satisfaction</span>
              <span className="font-semibold text-green-600">{analyticsData.qualityMetrics.clientSatisfaction}/5.0</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Goal Achievement</span>
              <span className="font-semibold text-blue-600">{analyticsData.qualityMetrics.treatmentGoalAchievement}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Session Utilization</span>
              <span className="font-semibold text-purple-600">{analyticsData.qualityMetrics.sessionUtilization}%</span>
            </div>
          </div>
        </div>

        {/* Risk Management */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Shield className="h-5 w-5 text-red-600" />
            Safety & Risk
          </h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Risk Episodes</span>
              <span className="font-semibold text-red-600">{analyticsData.riskManagement.riskEpisodes}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Safety Plans Activated</span>
              <span className="font-semibold text-orange-600">{analyticsData.riskManagement.safetyPlanActivations}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Response Time</span>
              <span className="font-semibold text-green-600">{analyticsData.riskManagement.averageResponseTime}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ROI Summary */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl shadow-lg p-6 text-white">
        <h2 className="text-xl font-semibold mb-4">Return on Investment Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <p className="text-3xl font-bold">67%</p>
            <p className="text-blue-100">Time Savings per Session</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold">98%</p>
            <p className="text-blue-100">Documentation Accuracy</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold">30s</p>
            <p className="text-blue-100">Average Risk Detection</p>
          </div>
        </div>
      </div>
    </div>
  );
}
