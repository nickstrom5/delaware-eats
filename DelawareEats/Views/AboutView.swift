import SwiftUI

struct AboutView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("DELAWARE EATS").displayFont(32).foregroundStyle(Theme.green)
                    Text("A free guide to \(model.restaurantCount.formatted()) Delaware restaurants, with hand-checked lists of Delaware's own food (\(guideNames)), James Beard honors, and the Division of Public Health's own inspection records. No account, no ads, no tracking.")
                        .font(.subheadline).foregroundStyle(Theme.ink2)
                    Text("Delaware Eats is an independent app by Nicholas Soderstrom. It is not affiliated with, endorsed by or operated by the State of Delaware, the Delaware Department of Health and Social Services, the Division of Public Health or its Office of Food Protection, the Department of Finance or its Division of Revenue, the Office of the Alcoholic Beverage Control Commissioner, the Delaware Tourism Office, the University of Delaware, the James Beard Foundation, Apple, or any restaurant or chain. Other names are trademarks of their owners.")
                        .font(.footnote).foregroundStyle(Theme.muted)
                }
                .padding(.vertical, 4)
            }
            Section("How the lists are built") {
                Text("The food lists (\(guideNames)) are hand-checked: each place was checked against a 2025 or 2026 source (the place's own website or menu, local news, an official tourism listing, or a 2025–26 DPH inspection), with the address checked. Founding years mean the year it opened at this address.")
                Text("Honors are James Beard Foundation nominations for the restaurant or its chef. Delaware has no MICHELIN Guide.")
                Text("Places start from open map listings (Overture Maps). The Division of Public Health inspects every food establishment in Delaware, so the listings were checked statewide against DPH's establishments: high-confidence listings matched one \(rate("meta_high")) of the time, and the app keeps the kinds that proved reliable. Places matched to an establishment DPH inspected in the past two years, or to a current Delaware restaurant license, are marked official, and inspected restaurants the map data missed are added. A place DPH marks closed is left out, even when its business license is still valid. Adult clubs are left out. Website links are checked, and any that no longer belong to the place are left out.")
                Text("Inspection records are DPH's own: each inspection's date and type (routine, follow-up or complaint) and each Food Code section cited, by number and title. Delaware has no official grade, score or placard, and DPH doesn't say which citations were priority items, so this app counts every section the same and computes no grade.")
                Text("Ratings, reviews, hours and photos are Apple Maps' own, shown live in Apple's place card. This app doesn't store or rank by them.")
            }
            .font(.subheadline).foregroundStyle(Theme.ink2)
            Section("Sources") {
                source("Delaware Division of Public Health", "Food Establishment Inspection Violations (data.delaware.gov), published by the Department of Health and Social Services, Division of Public Health, Office of Food Protection, in the public domain and updated weekly: the past two years of inspections. Inspections through \(DayFormat.text(model.dphThrough) ?? ""), shown as published; names shortened to the business name, and modified for use in this app. DPH's own note: \u{201C}If you have questions regarding a food inspection report, whether currently reported or for a prior reporting period, please contact the Office of Food Protection at 302-744-4546.\u{201D}", Links.dphInspections.absoluteString)
                source("Delaware Division of Revenue", "Delaware Business Licenses (data.delaware.gov), published by the Department of Finance, Division of Revenue, in the public domain and updated daily: current licenses in the Retailer – Restaurant activity, with the trade name, license number and the date each is valid through. Owners' legal names are not shown.", Links.businessLicenses.absoluteString)
                source("Overture Maps Foundation", "Restaurant listings and websites come from Overture Maps Foundation places data (overturemaps.org)\(model.overtureRelease.map { ", release \($0)" } ?? ""), filtered and reformatted for this app.\n• Data from Meta, Microsoft, DAC and BrightQuery. Available under CDLA Permissive 2.0.\n• Data from Foursquare. \(foursquareCopyright) Available under Apache 2.0. Foursquare data was transformed to the Overture schema; this app further filtered and reformatted it. See the NOTICE below.\n• Data from AllThePlaces. Available under CC0 1.0.", "https://overturemaps.org")
                source("Honors", "James Beard Foundation finalists and semifinalists are reported as facts and checked by hand against the official announcements. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Other names belong to their owners.", "https://www.jamesbeard.org/awards")
                source("Maps", "Maps, place cards and directions by Apple Maps.", nil)
            }
            Section("Licenses") {
                NavigationLink("Community Data License Agreement – Permissive 2.0") { LicenseText(file: "CDLA-Permissive-2.0", title: "CDLA Permissive 2.0") }
                NavigationLink("Apache License 2.0") { LicenseText(file: "Apache-2.0", title: "Apache License 2.0") }
                NavigationLink("Foursquare OS Places NOTICE") { LicenseText(file: "Foursquare-NOTICE", title: "Foursquare NOTICE") }
            }
            Section("Privacy") {
                Text("The app collects nothing. Your location, if you allow it, only sorts lists by distance and shows where you are on the map, on this device. Saved places stay on this device.")
                    .font(.subheadline).foregroundStyle(Theme.ink2)
                DataUpdatesNote()
                    .font(.footnote).foregroundStyle(Theme.muted)
                Link("Privacy policy", destination: Links.privacy)
                Link("Terms of use", destination: Links.terms)
            }
            Section("Help") {
                Link("Report a missing or closed place", destination: Links.correctionEmail)
                Link("Email \(Links.supportEmail)", destination: URL(string: "mailto:\(Links.supportEmail)")!)
                Link("Website", destination: Links.site)
                Text("Data as of \(DayFormat.text(model.generated) ?? model.generated). Places open and close; check before you go. Version \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0")")
                    .font(.footnote).foregroundStyle(Theme.muted)
            }
        }
        .navigationTitle("About")
        .tint(Theme.green)
    }

    /// the copyright line exactly as the bundled Foursquare NOTICE has it, so the two can't disagree
    private var foursquareCopyright: String {
        guard let url = Bundle.main.url(forResource: "Foursquare-NOTICE", withExtension: "txt"),
              let text = try? String(contentsOf: url, encoding: .utf8),
              let line = text.split(separator: "\n").first(where: { $0.hasPrefix("©") }) else { return "© Foursquare Labs, Inc. All rights reserved." }
        return line.trimmingCharacters(in: .whitespaces)
    }

    /// the hand-checked guides that have places, as the Home screen shows them (the data decides, not a promise in the copy)
    private var guideNames: String {
        Guide.allCases.filter { $0.tag != nil && model.count($0) > 0 }.map { $0.title.lowercased() }.joined(separator: ", ")
            .replacingOccurrences(of: "wilmington italian", with: "Wilmington Italian")
    }

    /// the statewide share (the per-county shares are on the site's sources page)
    private func rate(_ group: String) -> String {
        guard let v = model.calibration.areas["Delaware"]?.groups[group]?.official else { return "most" }
        return "\(Int((v * 100).rounded()))%"
    }

    @ViewBuilder
    private func source(_ name: String, _ detail: String, _ url: String?) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            if let url, let u = URL(string: url) { Link(name, destination: u).font(.subheadline.weight(.semibold)) }
            else { Text(name).font(.subheadline.weight(.semibold)) }
            Text(detail).font(.caption).foregroundStyle(Theme.muted)
        }
    }
}

/// A bundled license text (Resources/Licenses), reflowed rather than shown as raw 80-column lines.
struct LicenseText: View {
    let file: String
    let title: String

    var body: some View {
        ScrollView {
            Text(text).font(.footnote).foregroundStyle(Theme.ink).textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading).padding()
        }
        .inlineTitle(title)
    }

    private var text: String {
        guard let url = Bundle.main.url(forResource: file, withExtension: "txt"),
              let raw = try? String(contentsOf: url, encoding: .utf8) else { return "License text missing." }
        // join hard-wrapped lines into paragraphs; keep blank lines and list items as breaks
        var out: [String] = []
        for para in raw.components(separatedBy: "\n\n") {
            let lines = para.components(separatedBy: "\n").map { $0.trimmingCharacters(in: .whitespaces) }
            var joined = ""
            for l in lines where !l.isEmpty {
                let startsItem = l.hasPrefix("–") || l.hasPrefix("-") || l.range(of: #"^\(?[a-z0-9]{1,3}[.)]\s"#, options: .regularExpression) != nil
                joined += joined.isEmpty ? l : (startsItem ? "\n" + l : " " + l)
            }
            if !joined.isEmpty { out.append(joined) }
        }
        return out.joined(separator: "\n\n")
    }
}
