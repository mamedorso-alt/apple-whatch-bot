import SwiftUI

struct ReportsView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                DashboardCard(title: String(localized: "reports.title")) {
                    if viewModel.isLinked == false {
                        Text(String(localized: "reports.hint.link_first"))
                            .font(.footnote)
                            .foregroundStyle(AppTheme.warning)
                    }
                    if viewModel.hasTodayScore == false {
                        Text(String(localized: "reports.hint.no_today_score"))
                            .font(.footnote)
                            .foregroundStyle(.white.opacity(0.7))
                    }
                }

                HStack(spacing: 10) {
                    Button(String(localized: "reports.button.today")) {
                        Task { await viewModel.fetchTodayReport() }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.accent)
                    .disabled(viewModel.isLoading)

                    Button(String(localized: "reports.button.week")) {
                        Task { await viewModel.fetchWeekReport() }
                    }
                    .buttonStyle(.bordered)
                    .disabled(viewModel.isLoading)
                }

                if viewModel.todayReport.isEmpty == false {
                    DashboardCard(title: String(localized: "reports.section.today")) {
                        Text(viewModel.todayReport)
                            .foregroundStyle(.white.opacity(0.9))
                            .textSelection(.enabled)
                    }
                }

                if viewModel.weekReport.isEmpty == false {
                    DashboardCard(title: String(localized: "reports.section.week")) {
                        Text(viewModel.weekReport)
                            .foregroundStyle(.white.opacity(0.9))
                            .textSelection(.enabled)
                    }
                }

                if let error = viewModel.errorMessage {
                    Text(error).foregroundStyle(.red)
                }
            }
            .padding()
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(String(localized: "reports.title"))
        .task {
            await viewModel.refreshReportStatus()
        }
    }
}
