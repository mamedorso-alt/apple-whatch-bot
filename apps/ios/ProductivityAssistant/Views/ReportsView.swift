import SwiftUI

struct ReportsView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                if viewModel.isLinked == false {
                    Text(String(localized: "reports.hint.link_first"))
                        .font(.footnote)
                        .foregroundStyle(.orange)
                }
                if viewModel.hasTodayScore == false {
                    Text(String(localized: "reports.hint.no_today_score"))
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                HStack(spacing: 10) {
                    Button(String(localized: "reports.button.today")) {
                        Task { await viewModel.fetchTodayReport() }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(viewModel.isLoading)

                    Button(String(localized: "reports.button.week")) {
                        Task { await viewModel.fetchWeekReport() }
                    }
                    .buttonStyle(.bordered)
                    .disabled(viewModel.isLoading)
                }

                if viewModel.todayReport.isEmpty == false {
                    Text(String(localized: "reports.section.today"))
                        .font(.headline)
                    Text(viewModel.todayReport)
                        .textSelection(.enabled)
                }

                if viewModel.weekReport.isEmpty == false {
                    Text(String(localized: "reports.section.week"))
                        .font(.headline)
                    Text(viewModel.weekReport)
                        .textSelection(.enabled)
                }

                if let error = viewModel.errorMessage {
                    Text(error).foregroundStyle(.red)
                }
            }
            .padding()
        }
        .navigationTitle(String(localized: "reports.title"))
        .task {
            await viewModel.refreshReportStatus()
        }
    }
}
