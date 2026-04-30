import Foundation

struct WeeklyActivityPoint: Identifiable {
    let date: Date
    let steps: Double
    let activeKcal: Double

    var id: Date { date }
}
