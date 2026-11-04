import SwiftUI

struct HomeView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.horizontalSizeClass) private var sizeClass
    @State private var lastRandom: String?
    private let columns = [GridItem(.adaptive(minimum: 158), spacing: 12)]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                header
                Button { model.openGuide(.all) } label: {
                    HStack(spacing: 10) {
                        Image(systemName: "magnifyingglass").fontWeight(.bold).foregroundStyle(Theme.ink)
                        Text("Search by name, town or street").foregroundStyle(Theme.muted)
                        Spacer()
                    }
                    .font(.subheadline)
                    .padding(.horizontal, 16).padding(.vertical, 13)
                    .background(Capsule().fill(Theme.surface))
                    .overlay(Capsule().strokeBorder(Theme.ink, lineWidth: 2))
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Search every restaurant")
                LazyVGrid(columns: columns, spacing: 12) {
                    // a guide shows once its hand-checked research has places (the data decides, not a promise on a card)
                    ForEach([Guide.scrapple, .boardwalk, .crab, .dumplings, .italian, .creamery, .brewpub, .honors, .oldest, .inspections, .nearMe]
                        .filter { $0 == .nearMe || model.count($0) > 0 }) { g in
                        Button { model.openGuide(g) } label: { GuideCard(guide: g, count: model.count(g)) }
                            .buttonStyle(.plain)
                    }
                }
                surpriseButton
                Text("Ratings, hours and photos come live from Apple Maps on each place. Lists are built from open map data, the Division of Public Health's inspection records, the state's restaurant licenses and hand-checked research. See About for sources.")
                    .font(.footnote).foregroundStyle(Theme.muted)
            }
            .padding(16)
        }
        .background(Theme.sand)
        .navigationTitle("")
        .toolbar(.hidden, for: .navigationBar)
    }

    /// A boardwalk stand's sign: a small "First State" eyebrow, the title compressed and heavy in colonial blue with a hard buff
    /// shadow, and the Twelve-Mile Circle's arc under it.
    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "fork.knife").font(.caption.weight(.bold)).foregroundStyle(Theme.green2)
                Text("THE FIRST STATE").monoFont(12).tracking(0.5).foregroundStyle(Theme.green)
            }
            .accessibilityHidden(true)
            Text("DELAWARE EATS")
                .displayFont(72)
                .foregroundStyle(Theme.green)
                .lineLimit(1).minimumScaleFactor(0.6)
                .shadow(color: Theme.gold, radius: 0, x: 3, y: 3)
                .accessibilityLabel("Delaware Eats")
                .accessibilityAddTraits(.isHeader)
            Stripes().padding(.bottom, 2)
            Text("SCRAPPLE, CRABS & BOARDWALK")
                .displayFont(23, weight: .heavy).foregroundStyle(Theme.ink)
            Text("\(model.restaurantCount.formatted()) restaurants in \(model.towns.count.formatted()) Delaware towns, from Claymont to Fenwick Island, \(model.licensedCount.formatted()) of them on the state's inspection or license lists and \(model.inspectedCount.formatted()) with the Division of Public Health's latest routine inspection.")
                .font(.subheadline).foregroundStyle(Theme.ink2)
        }
        .padding(.top, 8)
    }

    private var surpriseButton: some View {
        Button {
            if let p = model.randomClassic(excluding: lastRandom) {
                lastRandom = p.id
                // iPhone pushes it; iPad shows it in the place column (a growing stack there would resurface after a size change)
                if sizeClass != .regular { model.guidesPath.append(.place(p)) }
                model.selectedPlace = p
            }
        } label: {
            HStack(spacing: 12) {
                Image(systemName: "dice").font(.title3.weight(.semibold)).foregroundStyle(Theme.ink)
                    .frame(width: 44, height: 44).background(Circle().fill(Theme.goldSoft))
                Text("Surprise me with a Delaware classic").font(.subheadline.weight(.bold))
                Spacer(minLength: 0)
            }
            .padding(12)
            .background(RoundedRectangle(cornerRadius: 14).fill(Theme.surface))
            .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Theme.green, style: StrokeStyle(lineWidth: 2, dash: [6, 4])))
        }
        .buttonStyle(.plain)
        .foregroundStyle(Theme.ink)
    }
}

/// A guide as a color block: the count big in the monospaced face, the name compressed and heavy. The hand-checked Delaware food
/// guides are buff under blue type, the honors blue under white; the utility guides (inspections, near me, everything) stay
/// white with an ink outline.
struct GuideCard: View {
    let guide: Guide
    let count: Int

    private var colors: (fill: Color, text: Color, number: Color) {
        switch guide {
        case .scrapple, .boardwalk, .crab, .dumplings, .italian, .creamery, .brewpub: (Theme.gold, Theme.green, Theme.green)
        case .honors, .oldest: (Theme.green, .white, .white)
        default: (Theme.surface, Theme.ink, Theme.green)
        }
    }

    var body: some View {
        let c = colors
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                if guide != .nearMe && guide != .all {   // "All" would just repeat the total in the header; Near Me has no fixed count
                    Text(count.formatted()).monoFont(30).foregroundStyle(c.number)
                } else {
                    Image(systemName: guide.systemImage).font(.title2.weight(.semibold)).foregroundStyle(c.number)
                }
                Spacer()
            }
            Spacer(minLength: 4)
            Text(guide.title.uppercased()).displayFont(20, weight: .heavy).foregroundStyle(c.text).fixedSize(horizontal: false, vertical: true)
            Text(guide.subtitle).font(.caption.weight(.medium)).foregroundStyle(c.text.opacity(0.9)).fixedSize(horizontal: false, vertical: true)
        }
        .padding(14)
        .frame(maxWidth: .infinity, minHeight: 150, alignment: .topLeading)
        .background(RoundedRectangle(cornerRadius: 18).fill(c.fill))
        .overlay { if c.fill == Theme.surface { RoundedRectangle(cornerRadius: 18).strokeBorder(Theme.ink, lineWidth: 2) } }
        // one reading of the count, after the title ("Scrapple Breakfasts. Hand-checked …", "12 places")
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(guide.title). \(guide.subtitle)")
        .accessibilityValue(guide != .nearMe && guide != .all ? "\(count) \(count == 1 ? "place" : "places")" : "")
    }
}
