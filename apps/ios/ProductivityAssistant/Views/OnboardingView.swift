import SwiftUI

struct OnboardingView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Apple Watch Productivity Assistant")
                .font(.title2)
                .bold()
            Text("Мы анализируем агрегаты активности, сна и нагрузки, чтобы дать вам короткие отчеты утром и вечером.")
            Text("We process daily aggregates from HealthKit and send productivity insights to your Telegram.")
            Text("Privacy: only aggregated daily metrics are sent.")
                .foregroundStyle(.secondary)
            Spacer()
        }
        .padding()
        .navigationTitle("Onboarding")
    }
}
