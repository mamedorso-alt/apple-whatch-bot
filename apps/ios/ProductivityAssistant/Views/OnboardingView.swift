import SwiftUI

struct OnboardingView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(String(localized: "onboarding.header"))
                .font(.title2)
                .bold()
            Text(String(localized: "onboarding.text.value"))
            Text(String(localized: "onboarding.text.integration"))
            Text(String(localized: "onboarding.text.privacy"))
                .foregroundStyle(.secondary)
            Spacer()
        }
        .padding()
        .navigationTitle(String(localized: "onboarding.title"))
    }
}
