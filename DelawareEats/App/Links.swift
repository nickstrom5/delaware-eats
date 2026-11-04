import Foundation

/// Every outside link the app opens, in one place. Each official page was checked to render (curl and a browser, 2026-10-27).
/// The site is GitHub Pages at the project address until delaware.eatsranked.com resolves (Nick adds a Cloudflare CNAME
/// delaware -> nickstrom5.github.io, DNS only; then scripts/make-site.py sets CUSTOM_DOMAIN). GitHub forwards these github.io
/// addresses to the custom domain once it's set, so a build with them keeps working.
enum Links {
    static let site = URL(string: "https://nickstrom5.github.io/delaware-eats/")!
    /// The app's data updates: scripts/publish_app_data.py writes docs/data/app/ (OTA-DATA.md).
    static let appData = URL(string: site.absoluteString + "data/app/")!
    static let privacy = URL(string: "https://nickstrom5.github.io/delaware-eats/privacy.html")!
    static let terms = URL(string: "https://nickstrom5.github.io/delaware-eats/terms.html")!
    /// the Division of Public Health's inspections and the Division of Revenue's business licenses (the portal's dataset pages)
    static let dphInspections = URL(string: "https://data.delaware.gov/Health/Food-Establishment-Inspection-Violations/384s-wygj")!
    static let businessLicenses = URL(string: "https://data.delaware.gov/Licenses-and-Certifications/Delaware-Business-Licenses/5zy2-grhr")!
    static let supportEmail = "nick@eatsranked.com"
    static var correctionEmail: URL {
        URL(string: "mailto:\(supportEmail)?subject=Delaware%20Eats%20correction")!
    }

    // MARK: Share

    /// The web app. It opens a place's panel from the hash, explore/#p=<id> (readHash in scripts/explore.js), using the app's ids.
    static let explore = URL(string: site.absoluteString + "explore/")!

    /// Whether the web app lists the place: make-site.py's rule (restaurants only; the venues the app hides by default, such as
    /// stadium stands and convenience-store counters, stay out).
    static func onWeb(_ place: Place) -> Bool { !place.isVenue }

    /// What Share sends: the place's own page in the web app, never an Apple Maps or Google link (Apple Maps has its own button).
    /// The id is escaped the way the page's encodeURIComponent would escape it. A place the web app leaves out gets the web app's
    /// front page, never a #p= link that opens nothing (a unit test checks the ids against docs/data).
    static func share(_ place: Place) -> URL {
        guard onWeb(place), let id = place.id.addingPercentEncoding(withAllowedCharacters: uriComponent),
              let url = URL(string: explore.absoluteString + "#p=" + id) else { return explore }
        return url
    }

    /// The text that goes with the link: the place, its town and the app. No street address, which Messages turns into a Maps link.
    static func shareMessage(_ place: Place) -> String {
        [place.name, place.city ?? ""].filter { !$0.isEmpty }.joined(separator: ", ") + ", on Delaware Eats"
    }

    /// What encodeURIComponent leaves as is.
    private static let uriComponent = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~*'()")
}
