import SwiftUI

struct HealthProfileView: View {
    @ObservedObject var viewModel: AppViewModel

    @State private var goalType = ""
    @State private var heightText = ""
    @State private var dietNotes = ""
    @State private var foodLogging = true
    @State private var maxAlerts = 3
    @State private var weightText = ""
    @State private var stressLevel = 2
    @State private var fatigueLevel = 2
    @State private var subjectiveNote = ""
    @State private var subjectiveSavedBanner: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                DashboardCard(title: String(localized: "health_profile.card.body")) {
                    VStack(alignment: .leading, spacing: 10) {
                        labeledField(title: String(localized: "health_profile.field.goal"), content: {
                            TextField("—", text: $goalType)
                                .textFieldStyle(.roundedBorder)
                                .foregroundStyle(.primary)
                        })
                        labeledField(title: String(localized: "health_profile.field.height"), content: {
                            TextField("cm", text: $heightText)
                                .keyboardType(.numberPad)
                                .textFieldStyle(.roundedBorder)
                                .foregroundStyle(.primary)
                        })
                        labeledField(title: String(localized: "health_profile.field.diet_notes"), content: {
                            TextField("", text: $dietNotes, axis: .vertical)
                                .lineLimit(3 ... 6)
                                .textFieldStyle(.roundedBorder)
                                .foregroundStyle(.primary)
                        })
                        Toggle(String(localized: "health_profile.field.food_logging"), isOn: $foodLogging)
                            .tint(AppTheme.accent)
                        Stepper(value: $maxAlerts, in: 0 ... 20) {
                            Text(String(format: String(localized: "health_profile.field.max_alerts"), maxAlerts))
                                .foregroundStyle(.white.opacity(0.9))
                        }
                    }
                }

                DashboardCard(title: String(localized: "health_profile.card.subjective")) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(String(localized: "health_profile.subjective.scale_hint"))
                            .font(.caption)
                            .foregroundStyle(.white.opacity(0.65))
                        stepperRow(title: String(localized: "health_profile.subjective.stress"), value: $stressLevel)
                        stepperRow(title: String(localized: "health_profile.subjective.fatigue"), value: $fatigueLevel)
                        labeledField(title: String(localized: "health_profile.subjective.note_optional"), content: {
                            TextField("", text: $subjectiveNote, axis: .vertical)
                                .lineLimit(2 ... 4)
                                .textFieldStyle(.roundedBorder)
                                .foregroundStyle(.primary)
                        })
                        Button(String(localized: "health_profile.subjective.save")) {
                            Task { await saveSubjective() }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(AppTheme.accent)
                        .disabled(viewModel.isLoading)
                        if let banner = subjectiveSavedBanner {
                            Text(banner)
                                .font(.footnote)
                                .foregroundStyle(AppTheme.success)
                        }
                    }
                }

                DashboardCard(title: String(localized: "health_profile.card.weight")) {
                    VStack(alignment: .leading, spacing: 8) {
                        if let last = viewModel.userProfile?.lastWeightKg {
                            Text(String(format: String(localized: "health_profile.last_weight"), String(format: "%.1f", last)))
                                .font(.footnote)
                                .foregroundStyle(.white.opacity(0.75))
                        }
                        HStack {
                            TextField(String(localized: "health_profile.weight.placeholder"), text: $weightText)
                                .keyboardType(.decimalPad)
                                .textFieldStyle(.roundedBorder)
                                .foregroundStyle(.primary)
                            Button(String(localized: "health_profile.weight.save")) {
                                Task { await saveWeight() }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(AppTheme.accent)
                            .disabled(viewModel.isLoading || Double(weightText.replacingOccurrences(of: ",", with: ".")) == nil)
                        }
                    }
                }

                Button(String(localized: "health_profile.save_profile")) {
                    Task { await saveProfile() }
                }
                .buttonStyle(.borderedProminent)
                .tint(AppTheme.accent)
                .frame(maxWidth: .infinity)
                .disabled(viewModel.isLoading)

                if let err = viewModel.errorMessage {
                    Text(err)
                        .foregroundStyle(.red)
                        .font(.footnote)
                }
            }
            .padding()
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(String(localized: "health_profile.title"))
        .task {
            await viewModel.loadUserProfile()
            applyFromProfile()
        }
    }

    private func labeledField<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.65))
            content()
        }
    }

    private func applyFromProfile() {
        guard let p = viewModel.userProfile else { return }
        goalType = p.goalType ?? ""
        if let h = p.heightCm {
            heightText = "\(h)"
        }
        dietNotes = p.dietNotes ?? ""
        foodLogging = p.foodLoggingEnabled
        maxAlerts = p.maxAlertsPerDay
    }

    private func saveProfile() async {
        let h = Int(heightText.trimmingCharacters(in: .whitespaces))
        let patch = UserProfilePatch(
            heightCm: h,
            goalType: goalType.isEmpty ? nil : goalType,
            dietNotes: dietNotes.isEmpty ? nil : dietNotes,
            foodLoggingEnabled: foodLogging,
            maxAlertsPerDay: maxAlerts
        )
        await viewModel.saveUserProfile(patch: patch)
        applyFromProfile()
    }

    private func saveWeight() async {
        let raw = weightText.replacingOccurrences(of: ",", with: ".")
        guard let w = Double(raw), w > 0 else { return }
        await viewModel.postUserWeight(weightKg: w)
        weightText = ""
    }

    private func stepperRow(title: String, value: Binding<Int>) -> some View {
        Stepper(value: value, in: 0 ... 5) {
            Text(String(format: String(localized: "health_profile.subjective.stepper_format"), title, value.wrappedValue))
                .foregroundStyle(.white.opacity(0.9))
        }
    }

    private func saveSubjective() async {
        subjectiveSavedBanner = nil
        let note = subjectiveNote.trimmingCharacters(in: .whitespacesAndNewlines)
        await viewModel.postTodaySubjective(
            stress: stressLevel,
            fatigue: fatigueLevel,
            note: note.isEmpty ? nil : note
        )
        if viewModel.errorMessage == nil {
            subjectiveSavedBanner = String(localized: "health_profile.subjective.saved")
        }
    }
}
