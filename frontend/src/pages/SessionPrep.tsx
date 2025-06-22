// src/pages/SessionPrep.tsx
import { CheckCircle2, Circle, Target, TrendingUp, Calendar, AlertTriangle, FileText } from "lucide-react";

interface SessionPrepData {
  lastSessionDate: string;
  lastSessionGoals: string[];
  homeworkTasks: Array<{
    task: string;
    completed: boolean;
    notes?: string;
  }>;
  recentAssessments: Array<{
    type: string;
    score: number;
    date: string;
    change: number;
  }>;
  flaggedConcerns: string[];
  suggestedTopics: string[];
  sessionGoals: string[];
}

export default function SessionPrep() {
  const sessionData: SessionPrepData = {
    lastSessionDate: "2024-01-15",
    lastSessionGoals: [
      "Practice daily mindfulness meditation for 10 minutes",
      "Implement sleep hygiene routine",
      "Use grounding techniques when feeling anxious"
    ],
    homeworkTasks: [
      { task: "Daily mood tracking (7 days)", completed: true, notes: "Completed 6/7 days - missed Sunday" },
      { task: "Practice 4-7-8 breathing technique", completed: true, notes: "Used 3x during work stress" },
      { task: "Complete thought record worksheet", completed: false, notes: "Started but didn't finish" },
      { task: "Schedule self-care activities", completed: true, notes: "Planned yoga class and coffee with friend" }
    ],
    recentAssessments: [
      { type: "PHQ-9", score: 14, date: "2024-01-12", change: -3 },
      { type: "GAD-7", score: 11, date: "2024-01-12", change: -2 }
    ],
    flaggedConcerns: [
      "Sleep quality remains poor despite interventions",
      "Work stress increasing due to project deadlines",
      "Mentioned feeling 'overwhelmed' multiple times in homework"
    ],
    suggestedTopics: [
      "Review and adjust sleep hygiene strategies",
      "Explore workplace stress management techniques", 
      "Discuss progress on thought challenging exercises",
      "Address upcoming work deadline anxiety"
    ],
    sessionGoals: [
      "Assess current coping strategy effectiveness",
      "Develop specific plan for work stress management",
      "Review and modify sleep routine",
      "Set realistic goals for next week"
    ]
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Session Preparation</h1>
        <p className="text-gray-600">Last session: {new Date(sessionData.lastSessionDate).toLocaleDateString()}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Homework Adherence */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            Homework Adherence
          </h2>
          <div className="space-y-4">
            {sessionData.homeworkTasks.map((task, index) => (
              <div key={index} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                {task.completed ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                ) : (
                  <Circle className="h-5 w-5 text-gray-400 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className={`font-medium ${task.completed ? 'text-gray-900' : 'text-gray-600'}`}>
                    {task.task}
                  </p>
                  {task.notes && (
                    <p className="text-sm text-gray-600 mt-1">{task.notes}</p>
                  )}
                </div>
              </div>
            ))}
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Completion Rate:</strong> {Math.round((sessionData.homeworkTasks.filter(t => t.completed).length / sessionData.homeworkTasks.length) * 100)}%
              </p>
            </div>
          </div>
        </div>

        {/* Recent Assessment Changes */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-blue-600" />
            Assessment Changes
          </h2>
          <div className="space-y-4">
            {sessionData.recentAssessments.map((assessment, index) => (
              <div key={index} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-gray-900">{assessment.type}</h3>
                  <div className="flex items-center gap-2">
                    <span className="text-xl font-bold text-gray-900">{assessment.score}</span>
                    <span className={`text-sm font-medium ${
                      assessment.change < 0 ? 'text-green-600' : assessment.change > 0 ? 'text-red-600' : 'text-gray-600'
                    }`}>
                      {assessment.change > 0 ? '+' : ''}{assessment.change}
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Last assessed: {new Date(assessment.date).toLocaleDateString()}</span>
                  <span className={`px-2 py-1 rounded text-xs ${
                    assessment.change < 0 ? 'bg-green-100 text-green-800' : 
                    assessment.change > 0 ? 'bg-red-100 text-red-800' : 
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {assessment.change < 0 ? 'Improved' : assessment.change > 0 ? 'Increased' : 'No Change'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Flagged Concerns */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-600" />
            Flagged Concerns
          </h2>
          <div className="space-y-3">
            {sessionData.flaggedConcerns.map((concern, index) => (
              <div key={index} className="flex items-start gap-3 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                <AlertTriangle className="h-4 w-4 text-orange-600 mt-0.5" />
                <p className="text-orange-800 text-sm">{concern}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Suggested Discussion Topics */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5 text-purple-600" />
            Suggested Topics
          </h2>
          <div className="space-y-2">
            {sessionData.suggestedTopics.map((topic, index) => (
              <div key={index} className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg">
                <div className="w-2 h-2 bg-purple-600 rounded-full"></div>
                <p className="text-purple-900 text-sm">{topic}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Session Goals */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Target className="h-5 w-5 text-green-600" />
          Recommended Session Goals
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sessionData.sessionGoals.map((goal, index) => (
            <div key={index} className="flex items-start gap-3 p-4 border border-green-200 bg-green-50 rounded-lg">
              <Target className="h-4 w-4 text-green-600 mt-1" />
              <p className="text-green-800 text-sm font-medium">{goal}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Start Session
          </button>
          <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
            Review Last Notes
          </button>
          <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
            Update Treatment Plan
          </button>
          <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
            Send Pre-Session Message
          </button>
        </div>
      </div>
    </div>
  );
}
