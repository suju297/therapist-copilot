// src/pages/PatientOverview.tsx
import { Calendar, FileText, AlertCircle, TrendingUp, Clock, Phone, Mail } from "lucide-react";

interface PatientData {
  name: string;
  age: number;
  dateOfBirth: string;
  phone: string;
  email: string;
  emergencyContact: string;
  diagnosis: string[];
  medications: string[];
  allergies: string[];
  lastSession: string;
  totalSessions: number;
  phq9Score: number;
  gad7Score: number;
  riskLevel: "none" | "low" | "medium" | "high";
}

interface PatientOverviewProps {
  patient?: PatientData;
}

export default function PatientOverview({ patient }: PatientOverviewProps) {
  // Sample patient data
  const defaultPatient: PatientData = {
    name: "Sarah Johnson",
    age: 28,
    dateOfBirth: "1995-03-15",
    phone: "(555) 123-4567",
    email: "sarah.j@email.com",
    emergencyContact: "Mark Johnson (Spouse) - (555) 987-6543",
    diagnosis: ["F32.1 Major Depressive Disorder, Moderate", "F41.1 Generalized Anxiety Disorder"],
    medications: ["Sertraline 50mg daily", "Lorazepam 0.5mg as needed"],
    allergies: ["Penicillin", "Shellfish"],
    lastSession: "2024-01-15",
    totalSessions: 12,
    phq9Score: 14,
    gad7Score: 11,
    riskLevel: "medium"
  };

  const patientData = patient || defaultPatient;

  const assessmentScores = [
    { name: "PHQ-9", score: patientData.phq9Score, max: 27, category: "Depression", 
      interpretation: patientData.phq9Score >= 15 ? "Moderately Severe" : patientData.phq9Score >= 10 ? "Moderate" : "Mild" },
    { name: "GAD-7", score: patientData.gad7Score, max: 21, category: "Anxiety",
      interpretation: patientData.gad7Score >= 15 ? "Severe" : patientData.gad7Score >= 10 ? "Moderate" : "Mild" }
  ];

  const recentActivity = [
    { date: "2024-01-15", type: "Session", note: "Discussed coping strategies for work stress" },
    { date: "2024-01-12", type: "Homework", note: "Completed mood tracking - 5/7 days" },
    { date: "2024-01-08", type: "Assessment", note: "PHQ-9 score improved from 17 to 14" },
    { date: "2024-01-01", type: "Session", note: "Set goals for new year, reviewed progress" }
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{patientData.name}</h1>
            <p className="text-gray-600">Age {patientData.age} • {patientData.totalSessions} sessions completed</p>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${
            patientData.riskLevel === "high" ? "bg-red-100 text-red-800" :
            patientData.riskLevel === "medium" ? "bg-yellow-100 text-yellow-800" :
            "bg-green-100 text-green-800"
          }`}>
            {patientData.riskLevel === "none" ? "Low Risk" : `${patientData.riskLevel} Risk`}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Contact & Demographics */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-600" />
            Demographics & Contact
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-500">Date of Birth</label>
              <p className="text-gray-900">{new Date(patientData.dateOfBirth).toLocaleDateString()}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">Phone</label>
              <p className="text-gray-900 flex items-center gap-2">
                <Phone className="h-4 w-4" />
                {patientData.phone}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">Email</label>
              <p className="text-gray-900 flex items-center gap-2">
                <Mail className="h-4 w-4" />
                {patientData.email}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">Emergency Contact</label>
              <p className="text-gray-900">{patientData.emergencyContact}</p>
            </div>
          </div>
        </div>

        {/* Current Assessment Scores */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-green-600" />
            Current Assessment Scores
          </h2>
          <div className="space-y-4">
            {assessmentScores.map((assessment) => (
              <div key={assessment.name} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-gray-900">{assessment.name}</h3>
                  <span className="text-2xl font-bold text-blue-600">{assessment.score}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full" 
                    style={{ width: `${(assessment.score / assessment.max) * 100}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">{assessment.category}</span>
                  <span className="text-gray-700">{assessment.interpretation}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Medical Information */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            Medical Information
          </h2>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-500">Primary Diagnoses</label>
              <div className="mt-1 space-y-1">
                {patientData.diagnosis.map((dx, index) => (
                  <p key={index} className="text-gray-900 bg-gray-50 px-2 py-1 rounded text-sm">{dx}</p>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">Current Medications</label>
              <div className="mt-1 space-y-1">
                {patientData.medications.map((med, index) => (
                  <p key={index} className="text-gray-900 bg-blue-50 px-2 py-1 rounded text-sm">{med}</p>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">Known Allergies</label>
              <div className="mt-1 space-y-1">
                {patientData.allergies.map((allergy, index) => (
                  <p key={index} className="text-gray-900 bg-red-50 px-2 py-1 rounded text-sm">{allergy}</p>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity Timeline */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Clock className="h-5 w-5 text-purple-600" />
          Recent Activity
        </h2>
        <div className="space-y-4">
          {recentActivity.map((activity, index) => (
            <div key={index} className="flex items-start gap-4 pb-4 border-b border-gray-100 last:border-b-0">
              <div className="w-2 h-2 bg-blue-600 rounded-full mt-2"></div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-gray-900">{activity.type}</span>
                  <span className="text-sm text-gray-500">{new Date(activity.date).toLocaleDateString()}</span>
                </div>
                <p className="text-gray-700 text-sm">{activity.note}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
