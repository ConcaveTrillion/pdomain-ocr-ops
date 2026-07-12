An update on this, I know this has been a while.

MOST excitingly, I've built a simple command line interface to this OCR tool with GPU acceleration (NVIDIA and *maybe Apple Silicon*), called, not very excitingly, pd-ocr "public domain ocr".

This should, in theory, run on all three major OSes: Linux, Windows, and Mac.

Please note, it's still in a "beta" phase of both model training and testing. I'm confident enough that it does *at least* a good job as tesseract (and in many cases a lot better). I've tested it against several "easy" pages and seen nearly 99% matches to round P3 proofing results (there's always going to be the need for a human proofreader imho). on "harder" pages it still struggles with some things, but I hope with continued fine-tuning and training, it can get even better.

If you're interested in trying it out, (especially if you have a machine with a GPU, but it should work even on machines without), head over to https://github.com/pdomain/pdomain-ocr-cli and read through the installation instructions. Sadly, the GPU install is *not* as easy as I would like it to be, and in order to actually *run* on the GPU you need ~5-10GB of various GPU library dependencies.

Other things I've been working on, that *support* this tool:

- A python library "pdomain-book-tools" including:
   - OCR data classes for 'page', 'block', 'line', 'word' etc.
   - GPU-accelerated (+CPU) versions of image pre-processing functions to improve OCR. Includes GPU-accelerated weighted gray scale (like GIMP's "color-to-gray", but about 50x faster, and way better than standard gray scale when it comes to improving text visibility), automated noise removal with heuristics to prevent removal of printed material, page edge finding, etc.
   - PGDP-specific rules-based "text cleanup" to remove proofer markup, asterisks, conversion of [special characters] to unicode, conversion of double hyphens to em-dashes, etc.
   - useful automated "paragraph splitting" using indentation heuristics to properly group paragraphs (needs some more work here)

- A "pd-ocr-labeler" locally-runnable python web GUI which runs locally (not via jupyter notebook as before) and performs OCR + "ground truth" matching against P3 pages, and provides everything necessary to properly clean up both bounding boxes and text for export into training of ML OCR detectors and recognizers. In addition, it provides the ability to add classification tags for "italics", "small caps", "all caps", "drop caps", "blackletter", etc. Eventually I hope to train specific detection/KIE models for word types as well.

- A "pd-ocr-trainer" locally-runnable python web GUI which takes labeled pages, and trains a DocTR OCR detection and recognition model.  Current model vocabulary includes most characters that appear in most post-1800 European printed texts. It's easy to add additional characters to the model to be trained against as well.

I have labeled approximately 100 pages so far, and have seen excellent results. Note that this is true "OCR", there is no LLM or NLP prediction that "adds" unseen characters from the image based on context. Via fine tuning of the existing dbnet50 detection model and CRNN detection model, I'm getting close to 98% to 99% P3 match rates on unseen (by the model) pages. Multi-column pages that weren't pre-split by a content provider/manager still require a bit of cleanup of the "assignment of words to paragraphs" to "match" properly, but I am working on some heuristics and looking at some "page structure" ML models that might be able to help with that as well.

The next step in my plan is building (and possibly hosting on a cheap AWS hardware) a "content prep" application/GUI that I want to use to leverage the fast GPU image processing tooling, plus these updated OCR models, in order to improve the quality and speed of scan prep and OCR (and perhaps make available to others). I've been working on an architecture and thing something like this could be hosted for $10-$20 a month or less, with burst cost for GPU "inference" depending on usage ("Modal" offers ad-hoc GPU bill-by-the-minute GPU containers, ECS is available as well).

SPECIAL THANKS to Casey and
