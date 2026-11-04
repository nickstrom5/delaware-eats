import SwiftUI
import MapKit

struct PlaceDetailView: View {
    @Environment(AppModel.self) private var model
    @Environment(LocationService.self) private var location
    let place: Place

    @State private var mapItem: MKMapItem?
    @State private var lookingUp = false
    @State private var notOnAppleMaps = false
    @State private var appleMapsFailed = false
    /// DPH inspection history, the Revenue business license, phone and website, from places.json's detail (read with the places)
    @State private var detail: PlaceDetail?
    @State private var detailLoaded = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                header
                actions
                if let c = place.coordinate { mapSnippet(c) }
                if place.handChecked && (place.note != nil || place.dishes != nil || place.founded != nil || place.seasonal != nil) { checked }
                if place.hasHonors { honors }
                if let i = place.inspection { inspections(i) }
                records
                listing
            }
            .padding(16)
        }
        .background(Theme.surface)
        .inlineTitle(place.name)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button { model.toggleSaved(place) } label: {
                    Label(model.isSaved(place) ? "Saved" : "Save", systemImage: model.isSaved(place) ? "heart.fill" : "heart")
                }
                .accessibilityIdentifier("saveHeart")   // the Saved tab is also a "Saved" button
                ShareLink(item: Links.share(place), subject: Text(place.name), message: Text(Links.shareMessage(place))) { Label("Share", systemImage: "square.and.arrow.up") }
            }
        }
        .task(id: place.id) {
            detailLoaded = false
            detail = await model.detail(for: place)
            detailLoaded = true
        }
        .mapItemDetailSheet(item: $mapItem)
        .alert("Not on Apple Maps", isPresented: $notOnAppleMaps) {
            Button("Open Apple Maps anyway") { AppleMaps.openInMaps(place) }
            Button("OK", role: .cancel) {}
        } message: {
            Text("Apple Maps doesn't have a listing for \(place.name) at this spot, so there are no ratings or hours to show here.")
        }
        .alert("Couldn't reach Apple Maps", isPresented: $appleMapsFailed) {
            Button("Try again") { lookUp() }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Check your connection and try again.")
        }
    }

    /// Apple's place card for this place; "not on Apple Maps" only when Apple answered and had no listing here.
    private func lookUp() {
        lookingUp = true
        Task {
            let result = await AppleMaps.findItem(for: place)
            lookingUp = false
            switch result {
            case .found(let item): mapItem = item
            case .notListed: notOnAppleMaps = true
            case .failed: appleMapsFailed = true
            }
        }
    }

    // MARK: sections

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            // "LEWES · SUSSEX COUNTY" (the data's county names already end in "County")
            Text((place.city ?? "Delaware").uppercased() + (place.county.map { " · " + $0.uppercased() } ?? ""))
                .monoFont(12).tracking(0.4).foregroundStyle(Theme.green2)
            Text(place.name.uppercased())
                .displayFont(38).foregroundStyle(Theme.green)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Text([place.fullAddress, place.cuisine].filter { !$0.isEmpty }.joined(separator: " · "))
                .font(.subheadline).foregroundStyle(Theme.ink2)
                .textSelection(.enabled)
            if let here = model.screenshotLocation ?? location.location, let l = place.location {
                Text("\(here.milesText(to: l)) away").font(.subheadline).foregroundStyle(Theme.muted)
            }
            PlaceChips(place: place)
        }
    }

    private var actions: some View {
        VStack(spacing: 10) {
            Button { lookUp() } label: {
                HStack {
                    if lookingUp { ProgressView().tint(.white) } else { Image(systemName: "star.bubble") }
                    Text("Ratings, hours & photos").fontWeight(.semibold)
                    Spacer()
                    Text("Apple Maps").font(.caption).foregroundStyle(Theme.goldSoft)
                }
                .padding(14)
                .foregroundStyle(.white)
                .background(RoundedRectangle(cornerRadius: 12).fill(Theme.green))
            }
            .disabled(place.coordinate == nil || lookingUp)
            .accessibilityHint("Opens the Apple Maps place card with current ratings and hours")

            HStack(spacing: 10) {
                actionButton("Directions", "arrow.triangle.turn.up.right.diamond") { AppleMaps.openInMaps(place, directions: true) }
                if let phone = detail?.ph, let url = URL(string: "tel:\(phone.filter { $0.isNumber || $0 == "+" })") {
                    actionButton("Call", "phone") { UIApplication.shared.open(url) }
                }
                if let web = detail?.website {
                    actionButton("Website", "safari") { UIApplication.shared.open(web) }
                }
            }
        }
    }

    private func actionButton(_ title: String, _ icon: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Image(systemName: icon).font(.title3)
                Text(title).font(.caption.weight(.semibold))
            }
            .frame(maxWidth: .infinity, minHeight: 56)
            .foregroundStyle(Theme.green)
            .background(RoundedRectangle(cornerRadius: 12).strokeBorder(Theme.rule2))
        }
    }

    private func mapSnippet(_ c: CLLocationCoordinate2D) -> some View {
        Map(initialPosition: .region(MKCoordinateRegion(center: c, latitudinalMeters: 900, longitudinalMeters: 900)), interactionModes: []) {
            Marker(place.name, systemImage: "fork.knife", coordinate: c).tint(Theme.green)
        }
        .frame(height: 170)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .onTapGesture { AppleMaps.openInMaps(place) }
        .accessibilityLabel("Map of \(place.name). Opens Apple Maps.")
        .accessibilityAddTraits(.isButton)
    }

    private var checked: some View {
        section("Hand-checked") {
            VStack(alignment: .leading, spacing: 8) {
                if let note = place.note { Text(note).font(.subheadline).foregroundStyle(Theme.ink2) }
                if let d = place.dishes { fact("On the menu", d.components(separatedBy: "; ").joined(separator: ", ")) }
                if let f = place.founded {
                    fact("Open here since", "\(f)")
                    // the note explains the year; without a year it only repeated the description above
                    if let fn = place.foundedNote { Text(fn).font(.caption).foregroundStyle(Theme.ink2) }
                }
                if let sea = place.seasonal { fact("Season", sea) }
                Text("Checked by hand against a 2025 or 2026 source: the place's own site or menu, local news or an official tourism listing. Menus and hours change, and many beach-town places close for the winter while diners and crab houses keep short or seasonal hours, so check before you go.")
                    .font(.caption).foregroundStyle(Theme.ink2)
            }
        }
    }

    private var honors: some View {
        section("Honors") {
            VStack(alignment: .leading, spacing: 8) {
                ForEach(lines(place.jamesBeard, prefix: "James Beard: "), id: \.self) { l in
                    Label(l, systemImage: "rosette").font(.subheadline).foregroundStyle(Theme.ink)
                }
                Text("Honors are facts, not ratings. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation.")
                    .font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    private func inspections(_ i: InspectionRecord) -> some View {
        section("Inspections · Division of Public Health") {
            VStack(alignment: .leading, spacing: 10) {
                if let n = i.routineCount {
                    HStack(alignment: .center, spacing: 12) {
                        InspectionBadge(count: n, large: true)
                        Text("Latest routine inspection, \(DayFormat.text(i.routineDate) ?? i.routineDate ?? "")").font(.subheadline).foregroundStyle(Theme.ink2)
                    }
                }
                if i.hasLaterVisit {
                    Text("\(i.routineCount == nil ? "Latest visit" : "Then") \(model.visitType(i.lastType).lowercased()), \(DayFormat.text(i.lastDate) ?? i.lastDate): \(i.lastCount == 0 ? "nothing cited" : "\(i.lastCount) section\(i.lastCount == 1 ? "" : "s") cited")")
                        .font(.subheadline).foregroundStyle(Theme.ink2)
                }
                if !detailLoaded { ProgressView().tint(Theme.green) }
                // by position: two inspections can share a day
                ForEach(Array((detail?.inspection?.visits ?? []).enumerated()), id: \.offset) { _, v in
                    VStack(alignment: .leading, spacing: 3) {
                        HStack(alignment: .firstTextBaseline) {
                            Text(DayFormat.text(v.d) ?? v.d).font(.subheadline).monospacedDigit().foregroundStyle(Theme.ink2)
                            Spacer(minLength: 8)
                            Text("\(model.visitType(v.t)) · \(v.count == 0 ? "nothing cited" : "\(v.count) cited")")
                                .font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink).multilineTextAlignment(.trailing)
                        }
                        ForEach(v.codes, id: \.self) { c in
                            Text(c + (model.sectionTitle(c).isEmpty ? "" : " " + model.sectionTitle(c)))
                                .font(.caption).monospacedDigit().foregroundStyle(Theme.muted)
                        }
                    }
                    .accessibilityElement(children: .combine)
                }
                Text("As the Division of Public Health publishes them: each inspection's date and type, and each Food Code section cited, by number and title. A title names the rule that was cited (\u{201C}Controlling Pests\u{201D}), not what the inspector saw. Delaware has no official grade, score or placard, and DPH doesn't say which citations were priority items, so this app counts every section the same and computes no grade. Many citations are corrected during the visit, and a follow-up checks the rest. One inspection is a snapshot of one day. Inspections through \(DayFormat.text(model.dphThrough) ?? "").")
                    .font(.caption).foregroundStyle(Theme.muted)
                Link(destination: Links.dphInspections) {
                    Label("DPH's inspection records", systemImage: "arrow.up.right.square").font(.subheadline.weight(.semibold))
                }
                .foregroundStyle(Theme.green)
            }
        }
    }

    private var records: some View {
        section("Official records") {
            VStack(alignment: .leading, spacing: 8) {
                let ls = detail?.licenses ?? []
                ForEach(ls, id: \.self) { l in
                    kv(l.source + (l.id.map { " " + Self.unbroken($0) } ?? ""),
                       l.type + (l.validThrough.flatMap { DayFormat.text($0) }.map { " · valid through \($0)" } ?? ""))
                }
                if ls.isEmpty { kv("Business license", detailLoaded ? "— (none matched)" : "…") }
                kv("Serves alcohol", "— (unknown)")
                Text(recordsNote).font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    private var listing: some View {
        section("How we know it's here") {
            VStack(alignment: .leading, spacing: 8) {
                kv("Listed as", place.tier.label)
                if place.tier == .licensed {
                    kv("Official record", detailLoaded || place.inspection != nil
                       ? Self.officialRecord(inspected: place.inspection != nil, licensed: !(detail?.licenses.isEmpty ?? true)) : "…")
                }
                if place.chainCount >= 2 { kv("Locations in Delaware", place.chainCount.formatted()) }
                Text(listingNote).font(.caption).foregroundStyle(Theme.muted)
            }
        }
    }

    /// "200034400", never broken across lines
    /// Which official record put a place on the list: DPH when it has DPH inspections or no Revenue license (DPH files farm stands
    /// and golf clubs as non-food establishments, whose inspections the app doesn't show), else its Revenue license
    static func officialRecord(inspected: Bool, licensed: Bool) -> String {
        inspected || !licensed ? "Division of Public Health" : "Delaware business license"
    }

    private static func unbroken(_ id: String) -> String { id.replacingOccurrences(of: "-", with: "\u{2011}") }

    /// Where the licenses come from; a missing license is unknown, not "no".
    private var recordsNote: String {
        "The Division of Revenue licenses every restaurant business in Delaware. A license runs up to three years, so it shows the business is licensed, not that it's open, and a missing one means none matched this place's name and address, not that it's unlicensed. Delaware's alcohol commission publishes no license list, so this app can't say whether a place serves alcohol."
    }

    private var listingNote: String {
        let checked = place.handChecked
        if place.source == "research" {
            return "On our hand-checked list (checked against a 2025 or 2026 source). The open map data didn't list it as a place to eat, so it's placed from its own map listing or street address."
        }
        switch place.tier {
        case .licensed:
            return place.source == "official"
                ? "From the Division of Public Health's inspected establishments. The open map data didn't have it, so its location comes from DPH's record."
                : "Matched to a Division of Public Health establishment inspected in the past two years, or a current Delaware restaurant license."
        case .confirmed, .listing:
            let rate = model.matchRate(for: place)
            let base = place.tier == .confirmed
                ? "A high-confidence listing in Overture's open map data."
                : "A single listing in Overture's open map data, so it may be closed or misfiled."
            let measured = rate.map { " Checked statewide against the Division of Public Health's establishments, listings like this matched one \($0) of the time." } ?? ""
            return base + measured + (checked ? " It's also on our hand-checked list, checked against a 2025 or 2026 source." : "")
        }
    }

    // MARK: helpers

    private func lines(_ s: String?, prefix: String) -> [String] {
        (s ?? "").components(separatedBy: "; ").filter { !$0.isEmpty }.map { prefix + $0 }
    }

    private func section<Content: View>(_ title: String, @ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title.uppercased()).font(.caption.weight(.bold)).tracking(1).foregroundStyle(Theme.ink2)
            Divider()
            content()
        }
    }

    private func fact(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink)
            Text(value).font(.subheadline).foregroundStyle(Theme.ink2)
        }
    }

    @ViewBuilder
    private func kv(_ k: String, _ v: String?) -> some View {
        if let v {
            HStack(alignment: .firstTextBaseline) {
                Text(k).font(.subheadline).foregroundStyle(Theme.ink2)
                Spacer(minLength: 12)
                Text(v).font(.subheadline.weight(.semibold)).foregroundStyle(Theme.ink).multilineTextAlignment(.trailing)
            }
        }
    }
}

extension String {
    var nonEmpty: String? { isEmpty ? nil : self }
}
