import SwiftUI
import UIKit
import CoreText

/// Colonial blue and buff, Delaware's state colors (29 Del. C. § 306 names "arno blue" and "golden beige" with no hex; Nick's pick,
/// 2026-10-27), light only: blue #1F3B6F (10.9:1 on white) for titles, tint and accents; buff #E3C79A only ever as a fill under blue
/// text (6.7:1), never as text on white; link blue #33558F (7.4:1); a deep peach #B4544E (white text 4.9:1), the darker shade of the
/// peach-blossom accent #F4A7A3, for the hand-checked pins and swipe actions. No team or university colors. The names
/// `green`/`gold`/`red` are kept from Wisconsin Eats so the shared views read the same: here `green` is blue, `gold` buff, `red` peach.
enum Theme {
    static let green = Color(hex: 0x1F3B6F)      // colonial blue: titles, tint, primary text accents, cards under white text
    static let green2 = Color(hex: 0x33558F)     // link blue
    static let gold = Color(hex: 0xE3C79A)       // buff: fills under blue text (guide cards, top ranks)
    static let goldSoft = Color(hex: 0xF5EBD9)
    static let lime = Color(hex: 0xE3C79A)       // buff, the Twelve-Mile Circle stripe, fills only
    static let limeSoft = Color(hex: 0xF5EBD9)
    static let peach = Color(hex: 0xF4A7A3)      // peach blossom: the one dot on the arc, fills only
    static let sand = Color(hex: 0xF7F4EE)
    static let red = Color(hex: 0xB4544E)        // deep peach: hand-checked pins, chips under white text, swipe actions
    static let ink = Color(hex: 0x13213D)
    static let ink2 = Color(hex: 0x1F3B6F)
    static let muted = Color(hex: 0x56607A)
    static let surface = Color.white
    static let surface2 = Color(hex: 0xF7F4EE)
    static let surface3 = Color(hex: 0xEEE6D8)
    static let rule = Color(hex: 0xE4DDD0)
    static let rule2 = Color(hex: 0xC9BDA6)
}

extension Color {
    init(hex: UInt32) {
        self.init(red: Double((hex >> 16) & 0xFF) / 255, green: Double((hex >> 8) & 0xFF) / 255, blue: Double(hex & 0xFF) / 255)
    }
}

/// A small uppercase label: "STONE CRAB", "1 MICHELIN STAR".
struct Chip: View {
    enum Style { case gold, green, red, plain, dashed }
    let text: String
    var style: Style = .plain

    var body: some View {
        Text(text.uppercased())
            .font(.caption2.weight(.bold))
            .tracking(0.4)
            .padding(.horizontal, 7).padding(.vertical, 3)
            .foregroundStyle(style == .green || style == .red ? Color.white : style == .dashed ? Theme.muted : style == .gold ? Theme.ink : Theme.green)
            .background {
                RoundedRectangle(cornerRadius: 5).fill(style == .gold ? Theme.goldSoft : style == .green ? Theme.green : style == .red ? Theme.red
                                                       : style == .dashed ? .clear : Theme.surface2)
            }
            .overlay {
                if style == .dashed { RoundedRectangle(cornerRadius: 5).strokeBorder(Theme.rule2, style: StrokeStyle(lineWidth: 1, dash: [3, 2])) }
            }
            .accessibilityLabel(text)
    }
}

/// DPH's latest routine inspection, as published: "DPH · 3 Food Code sections cited" or "DPH · Nothing cited". One neutral style for
/// every count: Delaware publishes no grade, score or placard, and the app computes none, so the badge colours none in.
struct InspectionBadge: View {
    let count: Int
    var large = false

    var body: some View {
        Text((count == 0 ? "DPH · Nothing cited" : "DPH · \(count) section\(count == 1 ? "" : "s") cited").uppercased())
            .font(large ? .footnote.weight(.heavy) : .caption2.weight(.heavy))
            .tracking(0.4)
            .multilineTextAlignment(.leading)
            .padding(.horizontal, large ? 10 : 7).padding(.vertical, large ? 6 : 3)
            .foregroundStyle(Theme.ink2)
            .background(RoundedRectangle(cornerRadius: 6).fill(Theme.surface3))
            .accessibilityLabel(count == 0 ? "Division of Public Health inspection: nothing cited"
                                : "Division of Public Health inspection: \(count) Food Code section\(count == 1 ? "" : "s") cited")
    }
}

/// Delaware Eats' lettering: the system face drawn compressed and heavy for titles and guide names (like a chili parlor's sign), and the
/// system monospaced face for numbers, dates and small labels. No bundled fonts.
struct DisplayFont: ViewModifier {
    let size: CGFloat
    var weight: Font.Weight = .black
    @ScaledMetric(relativeTo: .body) private var scale: CGFloat = 1

    func body(content: Content) -> some View {
        content.font(.system(size: size * min(scale, 1.6), weight: weight).width(.compressed))
    }
}

/// Numbers, dates and small labels in the system monospaced face, scaled like DisplayFont.
struct MonoFont: ViewModifier {
    let size: CGFloat
    var weight: Font.Weight = .semibold
    @ScaledMetric(relativeTo: .body) private var scale: CGFloat = 1

    func body(content: Content) -> some View {
        content.font(.system(size: size * min(scale, 1.6), weight: weight, design: .monospaced))
    }
}

extension View {
    func displayFont(_ size: CGFloat, weight: Font.Weight = .black) -> some View {
        modifier(DisplayFont(size: size, weight: weight))
    }

    func monoFont(_ size: CGFloat, weight: Font.Weight = .semibold) -> some View {
        modifier(MonoFont(size: size, weight: weight))
    }
}

/// The Twelve-Mile Circle, the arc of Delaware's northern border, as a thin curved stripe under the Home title (the header element
/// Nick picked, 2026-10-27): a buff band under a blue line, with one peach-blossom dot where the arc meets the Delaware River. No seal,
/// flag or university marks. The name `Stripes` is kept from the other state apps' header bands.
struct Stripes: View {
    var height: CGFloat = 6

    var body: some View {
        ZStack(alignment: .trailing) {
            Arc().stroke(Theme.lime, style: StrokeStyle(lineWidth: height, lineCap: .round))
            Arc().stroke(Theme.green, style: StrokeStyle(lineWidth: max(1.5, height * 0.35), lineCap: .round))
            Circle().fill(Theme.peach).frame(width: height * 1.4, height: height * 1.4).offset(x: -height * 0.2, y: height * 0.9)
        }
        .frame(height: height * 3.5)
        .accessibilityHidden(true)
    }

    /// a shallow arc from the lower left corner to the lower right, peaking in the middle
    private struct Arc: Shape {
        func path(in r: CGRect) -> Path {
            var p = Path()
            p.move(to: CGPoint(x: r.minX + 2, y: r.maxY - 3))
            p.addQuadCurve(to: CGPoint(x: r.maxX - 2, y: r.maxY - 3), control: CGPoint(x: r.midX, y: r.minY - r.height * 0.6))
            return p
        }
    }
}

extension View {
    /// An inline navigation title in the display type. UINavigationBar.appearance() didn't reach every SwiftUI bar on iOS 27
    /// (the Map title went from compressed blue to plain black after a push and pop; place titles were always plain), so the
    /// title is our own view in the bar. The navigation title is still set, for the back button and VoiceOver.
    func inlineTitle(_ title: String) -> some View {
        navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text(title).displayFont(19, weight: .heavy).foregroundStyle(Theme.green)
                        .lineLimit(1).minimumScaleFactor(0.7)
                        .accessibilityAddTraits(.isHeader)
                }
            }
    }
}
