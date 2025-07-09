import React, { useState } from 'react';
import { AlertCircle, Shield, Eye, Share2, Mail, Download, CheckCircle, Copy } from 'lucide-react';

const PrivacyRightsRegistry = () => {
  const [step, setStep] = useState('register');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rights: {
      erasure: false,
      no_sale: false,
      no_profiling: false,
      no_marketing: false,
      data_portability: false,
      access_request: false,
      anti_doxxing: false
    }
  });
  const [userToken, setUserToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const rightsDescriptions = {
    erasure: {
      title: "Right to Erasure",
      description: "Companies must delete all personal data about you upon request",
      icon: <Shield className="w-5 h-5" />
    },
    no_sale: {
      title: "No Sale of Data",
      description: "Companies cannot sell your personal information to third parties",
      icon: <Share2 className="w-5 h-5" />
    },
    no_profiling: {
      title: "No Automated Profiling",
      description: "Companies cannot make automated decisions about you based on your data",
      icon: <Eye className="w-5 h-5" />
    },
    no_marketing: {
      title: "No Marketing Communications",
      description: "Companies cannot send you promotional emails, texts, or calls",
      icon: <Mail className="w-5 h-5" />
    },
    data_portability: {
      title: "Data Portability",
      description: "Companies must provide your data in a machine-readable format upon request",
      icon: <Download className="w-5 h-5" />
    },
    access_request: {
      title: "Right to Access",
      description: "Companies must provide details of all personal data they hold about you",
      icon: <CheckCircle className="w-5 h-5" />
    },
    anti_doxxing: {
      title: "Anti-Doxxing Protection",
      description: "Blocks data lookups to prevent stalking, harassment, and doxxing attempts",
      icon: <AlertCircle className="w-5 h-5" />
    }
  };

  const handleRightChange = (right: string, value: boolean) => {
    setFormData(prev => ({
      ...prev,
      rights: {
        ...prev.rights,
        [right]: value
      }
    }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        throw new Error('Registration failed');
      }

      const data = await response.json();
      setUserToken(data.token);
      setStep('success');
    } catch (err) {
      setError('Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const copyToken = async () => {
    try {
      await navigator.clipboard.writeText(userToken);
      alert('Token copied to clipboard!');
    } catch (err) {
      console.error('Failed to copy token:', err);
    }
  };

  if (step === 'success') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-600 to-blue-600 p-4">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-xl shadow-2xl p-8">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Privacy Rights Registered!
              </h1>
              <p className="text-gray-600">
                Your privacy rights are now legally enforceable. Companies that process your data without checking this registry are legally negligent.
              </p>
            </div>

            <div className="bg-gray-50 rounded-lg p-6 mb-6">
              <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Your Privacy Rights Token
              </h2>
              <div className="bg-white border rounded-lg p-4 mb-4">
                <code className="text-sm text-gray-800 break-all">{userToken}</code>
              </div>
              <button
                onClick={copyToken}
                className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                <Copy className="w-4 h-4" />
                Copy Token
              </button>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-yellow-800 mb-1">Keep This Token Safe</h3>
                  <p className="text-sm text-yellow-700">
                    This token is proof of your registered privacy rights. Companies can look it up to see what rights you've declared. Store it securely and reference it in any privacy-related communications.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="font-semibold text-gray-900">Your Registered Rights:</h3>
              {Object.entries(formData.rights).map(([right, enabled]) => {
                if (!enabled) return null;
                const description = rightsDescriptions[right as keyof typeof rightsDescriptions];
                return (
                  <div key={right} className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
                    <div className="text-green-600">{description.icon}</div>
                    <div>
                      <div className="font-medium text-green-800">{description.title}</div>
                      <div className="text-sm text-green-700">{description.description}</div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-8 p-4 bg-blue-50 rounded-lg">
              <h3 className="font-semibold text-blue-900 mb-2">What Happens Next?</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Companies processing your data should check this registry</li>
                <li>• Failure to check creates legal negligence for privacy violations</li>
                <li>• You can reference your token in any privacy complaints</li>
                <li>• Your rights are immediately enforceable under GDPR/CCPA</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 to-blue-600 p-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-xl shadow-2xl p-8">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Shield className="w-8 h-8 text-purple-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Privacy Rights Registry
            </h1>
            <p className="text-gray-600">
              Register your privacy rights to create legal due diligence obligations for companies
            </p>
          </div>

          <div className="space-y-6">
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  <span className="text-red-800">{error}</span>
                </div>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  required
                />
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Select Your Privacy Rights
              </h3>
              <div className="space-y-3">
                {Object.entries(rightsDescriptions).map(([right, description]) => (
                  <label key={right} className="flex items-start gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.rights[right as keyof typeof formData.rights]}
                      onChange={(e) => handleRightChange(right, e.target.checked)}
                      className="mt-1 h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-purple-600">{description.icon}</span>
                        <span className="font-medium text-gray-900">{description.title}</span>
                      </div>
                      <p className="text-sm text-gray-600">{description.description}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-blue-800 mb-1">How This Works</h3>
                  <p className="text-sm text-blue-700">
                    Once registered, companies can check this registry to see your privacy preferences. 
                    If they process your data without checking, they lose legal protection and become 
                    liable for privacy violations under existing GDPR/CCPA laws.
                  </p>
                </div>
              </div>
            </div>

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all disabled:opacity-50"
            >
              {loading ? 'Registering...' : 'Register Privacy Rights'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PrivacyRightsRegistry;