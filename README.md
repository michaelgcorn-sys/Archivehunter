# Archive Hunter

Search declassified and public-domain archives at once, then find your search words inside the documents.

**Searched together, one ranked list:** CIA reading room (via the Internet Archive's mirror), FBI Vault,
GWU National Security Archive, DOJ Epstein Library, Internet Archive, Library of Congress, NASA Technical
Reports, Dept of Energy (OSTI), Wikimedia Commons, UK National Archives.

**Explore tab:** browse by topic: hand-picked documents (verified against the source) plus live CIA finds.

**Ancient Intelligence tab:** real intelligence reports and diplomatic letters from Assyria, Egypt and Roman
Britain, with translations quoted from their scholarly editions and Met Museum photos.

**"Find my words inside"** reads the document (web page, text file or PDF, following a page to its PDF
when needed) and shows every passage containing your words, highlighted, with page numbers.
Scanned PDFs with no text layer can't be searched this way; the app says so.

**Browser links** for archives that can't be searched from a server: Black Vault, MuckRock, NSA, NRO,
Wilson Center, National Archives, Mary Ferrell, WAR.GOV UFO files, State Dept FOIA, FilesDropped.

## Run it
- Hosted: deploy `app.py` on https://share.streamlit.io (free), then open the link on any device.
- Locally: `pip install -r requirements.txt` then `streamlit run app.py`

## Private settings (Streamlit → Settings → Secrets)

Optional keys. Each feature switches on by itself when its key is present and stays hidden when it isn't.
None of these ever go in the code.

```toml
NARA_API_KEY = "..."            # U.S. National Archives Catalog (free: Catalog_API@nara.gov)

# Translation: add any ONE. Swapping services later is a settings change, not a rebuild.
DEEPL_API_KEY = "..."           # DeepL (free plan keys end in ":fx")
# GOOGLE_TRANSLATE_KEY = "..."  # Google Cloud Translation
# AZURE_TRANSLATOR_KEY = "..."  # Microsoft Translator (+ AZURE_TRANSLATOR_REGION = "eastus")
# TRANSLATE_PROVIDER = "deepl"  # only needed to choose when several keys are set
```

## Dossier links

`?doc=cia-readingroom-document-<id>` opens a CIA document as a dossier inside the app
(first page, key terms to follow, documents filed nearby, share link). Top Secret tiles and
CIA search results open dossiers.
