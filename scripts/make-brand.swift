// Delaware Eats brand: the app icon (Nick's pick 2026-10-27, concept B of scripts/icon-concepts.swift: boardwalk fries in an unbranded
// paper cup, on colonial blue), in the shared Eats Ranked style (../state-prompts/ICON-STYLE.md). Usage, from de-eats/:
// swift scripts/make-brand.swift -> DelawareEats/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png, the website's icons
// (docs/icon-512.png, icon-192.png, apple-touch-icon.png, favicon-32.png) and share image (docs/og.png).
import AppKit
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

func rgb(_ hex: UInt32) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 255) / 255, green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: 1)
}
let BLUE: UInt32 = 0x1F3B6F, BUFF: UInt32 = 0xE3C79A, PEACH: UInt32 = 0xF4A7A3

func roundRect(_ r: CGRect, _ rad: CGFloat) -> CGPath { CGPath(roundedRect: r, cornerWidth: rad, cornerHeight: rad, transform: nil) }

/// B: boardwalk fries in a paper cup (no brand): an upright cup, wider at the top, with one peach-blossom band, and the fries
/// standing up out of it at different heights in two golden tones. 6 colours.
func fries(_ c: CGContext, _ s: CGFloat) {
    let CUP: UInt32 = 0xFBF6EC, BAND: UInt32 = 0xF4A7A3, FRY: UInt32 = 0xF2C14E, FRY2: UInt32 = 0xF7D77F, RIM: UInt32 = 0xE3C79A
    let cx = 0.5 * s, cupTop = 0.505 * s, cupBot = 0.145 * s, topW = 0.40 * s, botW = 0.30 * s
    // fries: capsules from inside the cup up to their own heights (left to right), alternating tones
    let fryW: CGFloat = 0.078 * s
    let tops: [CGFloat] = [0.70, 0.80, 0.86, 0.79, 0.84, 0.73]
    for (i, t) in tops.enumerated() {
        let x = cx - 0.215 * s + CGFloat(i) * 0.0855 * s
        let r = CGRect(x: x - fryW / 2, y: cupTop - 0.10 * s, width: fryW, height: t * s - (cupTop - 0.10 * s))
        // a background-colour gap between neighbours (R7) so each fry reads on its own
        c.setStrokeColor(rgb(BLUE)); c.setLineWidth(20.0 / 1024 * s); c.setLineJoin(.round); c.addPath(roundRect(r, fryW / 2)); c.strokePath()
        c.setFillColor(rgb(i % 2 == 0 ? FRY : FRY2)); c.addPath(roundRect(r, fryW / 2)); c.fillPath()
    }
    // the cup
    let cup = CGMutablePath()
    cup.move(to: CGPoint(x: cx - botW / 2, y: cupBot)); cup.addLine(to: CGPoint(x: cx + botW / 2, y: cupBot))
    cup.addLine(to: CGPoint(x: cx + topW / 2, y: cupTop)); cup.addLine(to: CGPoint(x: cx - topW / 2, y: cupTop)); cup.closeSubpath()
    c.setFillColor(rgb(CUP)); c.addPath(cup); c.fillPath()
    c.saveGState(); c.addPath(cup); c.clip()
    c.setFillColor(rgb(BAND)); c.fill(CGRect(x: 0, y: 0.265 * s, width: s, height: 0.105 * s))
    c.setFillColor(rgb(RIM)); c.fill(CGRect(x: 0, y: cupTop - 0.035 * s, width: s, height: 0.035 * s))   // the rolled rim, a shade down
    c.restoreGState()
}

func save(_ ctx: CGContext, _ path: String) {
    let d = CGImageDestinationCreateWithURL(URL(fileURLWithPath: path) as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(d, ctx.makeImage()!, nil)
    guard CGImageDestinationFinalize(d) else { fatalError("could not write \(path)") }
    print("wrote", path)
}

func render(_ n: Int, _ path: String) {
    let ctx = CGContext(data: nil, width: n, height: n, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setShouldAntialias(true)
    ctx.setFillColor(rgb(BLUE)); ctx.fill(CGRect(x: 0, y: 0, width: n, height: n))
    fries(ctx, CGFloat(n))
    save(ctx, path)
}
render(1024, "DelawareEats/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png")
try? FileManager.default.createDirectory(atPath: "docs", withIntermediateDirectories: true)
for (n, name) in [(512, "icon-512.png"), (192, "icon-192.png"), (180, "apple-touch-icon.png"), (32, "favicon-32.png")] {
    render(n, "docs/" + name)
}

/// The share image (1200 x 630): colonial blue, the fries at the left, the name and tagline at the right, and the Twelve-Mile Circle's
/// arc along the bottom (a buff band under a thin white line, one peach-blossom dot at the river end).
func og(_ path: String) {
    let W = 1200, H = 630
    let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    ctx.setShouldAntialias(true)
    ctx.setFillColor(rgb(BLUE)); ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))
    let arc = CGMutablePath()
    arc.move(to: CGPoint(x: 0, y: 18)); arc.addQuadCurve(to: CGPoint(x: CGFloat(W), y: 18), control: CGPoint(x: CGFloat(W) / 2, y: 90))
    ctx.setLineCap(.round)
    ctx.setStrokeColor(rgb(BUFF)); ctx.setLineWidth(14); ctx.addPath(arc); ctx.strokePath()
    ctx.setStrokeColor(rgb(0xFFFFFF)); ctx.setLineWidth(3); ctx.addPath(arc); ctx.strokePath()
    ctx.setFillColor(rgb(PEACH)); ctx.fillEllipse(in: CGRect(x: CGFloat(W) - 52, y: 18, width: 22, height: 22))
    ctx.saveGState(); ctx.translateBy(x: 20, y: 60); fries(ctx, 540); ctx.restoreGState()
    let ns = NSGraphicsContext(cgContext: ctx, flipped: false)
    NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = ns
    let title = NSFont(name: "AvenirNextCondensed-Heavy", size: 112) ?? NSFont.boldSystemFont(ofSize: 104)
    let sub = NSFont(name: "AvenirNextCondensed-DemiBold", size: 44) ?? NSFont.boldSystemFont(ofSize: 40)
    NSAttributedString(string: "DELAWARE EATS", attributes: [.font: title, .foregroundColor: NSColor.white]).draw(at: NSPoint(x: 540, y: 330))
    NSAttributedString(string: "SCRAPPLE, CRABS & BOARDWALK", attributes: [.font: sub, .foregroundColor: NSColor(srgbRed: 0.89, green: 0.78, blue: 0.60, alpha: 1)]).draw(at: NSPoint(x: 544, y: 272))
    NSGraphicsContext.restoreGraphicsState()
    save(ctx, path)
}
og("docs/og.png")
