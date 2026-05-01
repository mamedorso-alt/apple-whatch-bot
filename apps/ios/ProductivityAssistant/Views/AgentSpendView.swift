import SwiftUI

struct AgentSpendView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(String(localized: "agent_spend.disclaimer"))
                    .font(.footnote)
                    .foregroundStyle(.white.opacity(0.65))

                DashboardCard(title: String(localized: "agent_spend.card.title")) {
                    spendRow(title: String(localized: "agent_spend.period.day"), amount: viewModel.agentSpendDayUsd)
                    spendRow(title: String(localized: "agent_spend.period.week"), amount: viewModel.agentSpendWeekUsd)
                    spendRow(title: String(localized: "agent_spend.period.month"), amount: viewModel.agentSpendMonthUsd)
                }
            }
            .padding()
        }
        .background(AppTheme.background.ignoresSafeArea())
        .navigationTitle(String(localized: "agent_spend.title"))
        .task {
            await viewModel.fetchAgentSpend()
        }
        .refreshable {
            await viewModel.fetchAgentSpend()
        }
    }

    private func spendRow(title: String, amount: Double) -> some View {
        HStack {
            Text(title)
                .foregroundStyle(.white.opacity(0.88))
            Spacer()
            Text(formatUsd(amount))
                .fontWeight(.semibold)
                .foregroundStyle(AppTheme.accent)
        }
        .padding(.vertical, 4)
    }

    private func formatUsd(_ value: Double) -> String {
        let f = NumberFormatter()
        f.numberStyle = .currency
        f.currencyCode = "USD"
        f.maximumFractionDigits = 4
        f.minimumFractionDigits = 2
        return f.string(from: NSNumber(value: value)) ?? String(format: "$%.2f", value)
    }
}
