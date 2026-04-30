import Charts
import SwiftUI

struct WeeklyActivityChartsView: View {
    private enum RangeOption: Int, CaseIterable, Identifiable {
        case week = 7
        case twoWeeks = 14
        case month = 30

        var id: Int { rawValue }
    }

    @ObservedObject var viewModel: AppViewModel

    private let dayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.setLocalizedDateFormatFromTemplate("EEE")
        return formatter
    }()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                DashboardCard(title: String(localized: "weekly_charts.range.title")) {
                    Picker(String(localized: "weekly_charts.range.title"), selection: $viewModel.weeklyActivityRangeDays) {
                        ForEach(RangeOption.allCases) { option in
                            Text(rangeLabel(option))
                                .tag(option.rawValue)
                        }
                    }
                    .pickerStyle(.segmented)
                    .onChange(of: viewModel.weeklyActivityRangeDays) { _, _ in
                        Task { await viewModel.fetchWeeklyActivity() }
                    }
                }

                Button(String(localized: "weekly_charts.button.refresh")) {
                    Task { await viewModel.fetchWeeklyActivity() }
                }
                .buttonStyle(.borderedProminent)
                .tint(AppTheme.accent)
                .disabled(viewModel.isLoading)

                if viewModel.weeklyActivity.isEmpty {
                    DashboardCard(title: String(localized: "weekly_charts.title")) {
                        Text(String(localized: "weekly_charts.empty"))
                            .font(.footnote)
                            .foregroundStyle(.white.opacity(0.7))
                    }
                } else {
                    DashboardCard(title: String(localized: "weekly_charts.section.steps")) {
                        Chart(viewModel.weeklyActivity) { point in
                            BarMark(
                                x: .value("Day", dayLabel(point.date)),
                                y: .value("Steps", point.steps)
                            )
                            .foregroundStyle(AppTheme.accent.gradient)
                            .annotation(position: .top) {
                                Text(Int(point.steps), format: .number)
                                    .font(.caption2)
                                    .foregroundStyle(.white.opacity(0.65))
                            }
                        }
                        .frame(height: 220)
                    }

                    DashboardCard(title: String(localized: "weekly_charts.section.kcal")) {
                        Chart(viewModel.weeklyActivity) { point in
                            BarMark(
                                x: .value("Day", dayLabel(point.date)),
                                y: .value("Active kcal", point.activeKcal)
                            )
                            .foregroundStyle(AppTheme.warning.gradient)
                            .annotation(position: .top) {
                                Text(Int(point.activeKcal), format: .number)
                                    .font(.caption2)
                                    .foregroundStyle(.white.opacity(0.65))
                            }
                        }
                        .frame(height: 220)
                    }
                }

                if let error = viewModel.errorMessage {
                    Text(error)
                        .foregroundStyle(.red)
                }
            }
            .padding()
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(String(localized: "weekly_charts.title"))
        .task {
            if viewModel.weeklyActivity.isEmpty {
                await viewModel.fetchWeeklyActivity()
            }
        }
    }

    private func dayLabel(_ date: Date) -> String {
        dayFormatter.string(from: date)
    }

    private func rangeLabel(_ option: RangeOption) -> String {
        switch option {
        case .week:
            return String(localized: "weekly_charts.range.7")
        case .twoWeeks:
            return String(localized: "weekly_charts.range.14")
        case .month:
            return String(localized: "weekly_charts.range.30")
        }
    }
}
