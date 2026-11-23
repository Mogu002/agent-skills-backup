import AppKit
import Foundation
import Vision

guard CommandLine.arguments.count == 4,
      let fps = Double(CommandLine.arguments[2]), fps > 0 else {
    fputs("usage: vision_ocr FRAME_DIR FPS OUTPUT_JSONL\n", stderr)
    exit(2)
}

let directory = URL(fileURLWithPath: CommandLine.arguments[1])
let output = URL(fileURLWithPath: CommandLine.arguments[3])
let files = try FileManager.default.contentsOfDirectory(
    at: directory, includingPropertiesForKeys: nil
).filter { ["jpg", "jpeg", "png"].contains($0.pathExtension.lowercased()) }
 .sorted { $0.lastPathComponent < $1.lastPathComponent }

FileManager.default.createFile(atPath: output.path, contents: nil)
let handle = try FileHandle(forWritingTo: output)
defer { try? handle.close() }

for (offset, file) in files.enumerated() {
    try autoreleasepool {
        guard let image = NSImage(contentsOf: file),
              let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return }
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = ["zh-Hans", "zh-Hant"]
        request.minimumTextHeight = 0.04
        try VNImageRequestHandler(cgImage: cgImage).perform([request])

        let observations = (request.results ?? []).compactMap { observation -> [String: Any]? in
            guard let candidate = observation.topCandidates(1).first else { return nil }
            return [
                "text": candidate.string,
                "confidence": candidate.confidence,
                "x": observation.boundingBox.minX,
                "y": observation.boundingBox.minY,
                "width": observation.boundingBox.width,
                "height": observation.boundingBox.height,
            ]
        }
        let record: [String: Any] = [
            "frame": file.lastPathComponent,
            "timestamp": Double(offset) / fps,
            "observations": observations,
        ]
        handle.write(try JSONSerialization.data(withJSONObject: record))
        handle.write(Data([0x0a]))
    }
    if (offset + 1) % 250 == 0 {
        fputs("processed \(offset + 1)/\(files.count)\n", stderr)
    }
}
