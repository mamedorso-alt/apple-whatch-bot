import SwiftUI

struct RootContentView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        TabView {
            NavigationStack {
                DashboardView(viewModel: viewModel)
            }
            .tabItem {
                Label(String(localized: "tab.dashboard"), systemImage: "square.grid.2x2.fill")
            }

            NavigationStack {
                WeeklyActivityChartsView(viewModel: viewModel)
            }
            .tabItem {
                Label(String(localized: "tab.activity"), systemImage: "chart.bar.xaxis")
            }

            NavigationStack {
                ReportsView(viewModel: viewModel)
            }
            .tabItem {
                Label(String(localized: "tab.coach"), systemImage: "brain.head.profile")
            }

            NavigationStack {
                ProfileHubView(viewModel: viewModel)
            }
            .tabItem {
                Label(String(localized: "tab.profile"), systemImage: "person.circle.fill")
            }
        }
    }
}
