import SwiftUI

struct HealthAccessView: View {
    @ObservedObject var viewModel: AppViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Разрешите доступ к HealthKit данным:")
            Text("- sleepAnalysis\n- stepCount\n- activeEnergyBurned\n- heartRate\n- restingHeartRate\n- heartRateVariabilitySDNN\n- workoutType")
                .font(.footnote)
                .foregroundStyle(.secondary)

            Button(viewModel.healthAccessGranted ? "Access Granted" : "Разрешить доступ") {
                Task { await viewModel.requestHealthAccess() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(viewModel.isLoading || viewModel.healthAccessGranted)

            if let error = viewModel.errorMessage {
                Text(error).foregroundStyle(.red)
            }

            Spacer()
        }
        .padding()
        .navigationTitle("Health Access")
    }
}
