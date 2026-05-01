import SwiftUI

struct InsightsView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                DashboardCard(title: String(localized: "insights.card.daily")) {
                    Text(viewModel.dailyInsightText.isEmpty ? String(localized: "insights.empty") : viewModel.dailyInsightText)
                        .font(.body)
                        .foregroundStyle(.white.opacity(0.92))
                        .frame(maxWidth: .infinity, alignment: .leading)
                }

                DashboardCard(title: String(localized: "insights.card.weekly")) {
                    Text(viewModel.weeklyInsightText.isEmpty ? String(localized: "insights.empty") : viewModel.weeklyInsightText)
                        .font(.body)
                        .foregroundStyle(.white.opacity(0.92))
                        .frame(maxWidth: .infinity, alignment: .leading)
                }

                Button(String(localized: "insights.refresh")) {
                    Task { await viewModel.fetchInsights() }
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
        .navigationTitle(String(localized: "insights.title"))
        .task {
            await viewModel.fetchInsights()
        }
    }
}
