# PRAMBH — TryHackMe Room Specification & Copy-Paste Deployment Document

> *Single-Task Architecture · Ten Cryptographic Milestones · Pure Lore Integration*
>
> **Operator Directive:** No external hints. Ten direct question-and-answer checkpoints. The internal grammar of the final title is nowhere revealed in plaintext — only *"four inks, one immutable order."*

---

## Task 1 — PRAMBH: The First Survey

### Task Configuration & Environment
- **Title:** `Task 1 - PRAMBH: The First Survey`
- **Material Distribution:** Downloadable Task Attachment (`prambh.zip.enc` + `MANIFEST.sha256`)
- **Execution Vector:** Offline / Isolated Host · **AttackBox:** Disabled · **Network:** Air-gapped
- **Estimated Completion Window:** 4 to 6 Hours (Enforced Sequential Machine Work & Stereoscopic Analysis)

---

### Task Description (Field Dossier)

#### The Valley Expedition (Winter 1983)

> *Before the Cartographer’s Ghost ever climbed the silent heights, there existed only the First Survey — PRAMBH.*
>
> In the dead winter of 1983, an expedition of field geodesists vanished into the forgotten valley works. Behind them remained an iron depot locked under cold protocol, eight subterranean granite vaults, an 8-bit computational loom whose silicon cycles consume sequential time, and a paper archive calculated to drown hasty minds.
>
> Folklore claims their zero milestone was swallowed by the mountain mist. The reality is far colder: few possess the endurance to pay the price in raw, unaccelerated machine work.
>
> You hold the single surviving depot parcel. It does not yield its inner truth to automated scrapers, decompilation scripts, or superficial guesses. The instruments here belong to an older doctrine of measurement — they observe unbroken silence. They offer no confirmation prompts, no diagnostic error banners, and no affirmations. Every wrong turn corroborates itself with plausible fiction, guiding the impatient down hours of elaborate, mathematical dead ends.
>
> *The only proof of an authentic journey is the final title.*

---

#### The Keeper's Triangulation Log (Station Perimeter Riddle)

> *The valley works were evacuated under cold protocol on 28 December 1983. The station keeper left the archive locked under a cryptographic ward whose unlock passphrase consists of **four single lowercase English words**, corresponding to the four physical survey landmarks of the station perimeter:*
>
> 1. **Station North (Perimeter Entry):** The heavy rusted swinging barrier that bars entry to the depot access road.
> 2. **Station Center (Thermal Core):** The stone recess where the coals of the winter fire were laid to sleep.
> 3. **Station West (Instrument Casing):** Element 30 on the periodic table; the dull bluish-white transition metal that shields the barometer housing from winter corrosion.
> 4. **Station South (The Open Plain):** The vast frozen clearing of white terrain stretching between the depot and the granite ridges.

---

#### The Immutable Law of Time
> This challenge is strictly offline. Its core mechanisms rely on deep memory-hard sequential chains that cannot be rented away, parallelized, or shortcut by cloud compute. Respect the clock. Maintain strict journals. Observe every artifact before assuming it is silent. The instruments record state progression locally into an authenticated ledger; tampering with the surveyor's ledger resets the measurement chain without warning.

---

#### Field Execution Protocol

Unseal the outer depot package using the four lowercase landmark words derived from the Keeper's Log:

```bash
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -in prambh.zip.enc -out prambh.zip -pass pass:"<word1 word2 word3 word4>"

unzip prambh.zip && cd prambh && sha256sum -c ../MANIFEST.sha256
```

Once within the unsealed depot directory, inspect `README_FOR_SOLVER.txt` and the primary survey markers. Each sector contains historical instruments, field notes, and recorded folios. Execute all instruments directly within the station environment; examine their usage instructions and consult the field folios to determine valid geodetic inputs.

---

### Questions & Field Inquiries

#### Question 1
*Before any surveyor set foot upon the high ridges, an initial benchmark was driven into the frozen earth at the threshold of the valley depot. The expedition keeper left the station locked under a quiet cryptographic ward, its key scattered silently within the opening testament without title or fanfare. Dispel the outer seal, call forth the first mechanical marker of the survey, and transcribe the immutable inscription carved upon the threshold stone.*
- **Answer:** `PRAMBH{zero_b8c1d72c}`

---

#### Question 2
*Buried beneath the zero marker lies a cold-rolled brass cylinder sealed against atmospheric moisture, its lockwork designed to defeat automated dictionary attacks and memory inspection. Only when addressed with the authentic six-word departure command inscribed upon the depot launch dispatch does the tumbler release its payload. Unlock the cylinder and transcribe the 64-hexadecimal primary load vector required to initialize the valley processor.*
- **Answer:** `96415166fc01091e7bce5b43d36a5d491cb6591f0471415e5f670535c7856392`

---

#### Question 3
*The computational loom operates on an 8-bit architecture whose memory-hard traversal stitches silicon cycles to sequential physical time. When driven by the authentic cartridge and loaded with the primary geodetic vector, the loom computes across half a gigabyte of volatile state. What intermediate checkpoint token is minted by the loom when claiming its state progression?*
- **Answer:** `PRAMBH{ec5ba654fe8e606a}`

---

#### Question 4
*Deep within the valley complex, the riddle mechanism guards access to the subterranean chambers. When interrogated with the loom's authentic claim, it yields the surveyor's settling verse that points to the solitary authentic vault amongst seven decoys. Transcribe the exact six-word verse revealed by the riddle mechanism.*
- **Answer:** `kiln weir sapling mantle hollow lunar`

---

#### Question 5
*Beneath the valley bedrock stretch eight subterranean chambers carved into the granite, identical in dimension, header format, and acoustic isolation. By speaking the true settling verse, the solitary authentic vault unseals its heavy stone threshold and reveals a 16-hexadecimal ink fragment carved into the pedestal. Transcribe this genuine door ink.*
- **Answer:** `66cb77c72ed791a7`

---

#### Question 6
*A persistent thread within the folios directs the investigator toward an alternate campaign known as the Duplicate Survey—complete with its own historical logs, independent chain walks, and a functional reception desk. For a weary solver, this parallel trail offers compelling corroboration. When an investigator completes this decoy labyrinth and files their findings at the duplicate desk, what deceptive title does the false validator emit?*
- **Answer:** `PRAMBH{mirror_5e7a0768329a6bbb}`

---

#### Question 7
*Once the seal is established and the surveyor’s viewing instructions are decrypted, the expedition's visual plates must be confronted. These artifacts resist naive machine vision, color-space filtering, and automated optical character recognition, hiding secondary decoy signals within their noise. Transcribe the complete 18-character composite eye ink formed by joining the three authentic six-glyph codes in normative order.*
- **Answer:** `Y22RGQ_9NK3HT_9UJYNG`

---

#### Question 8
*Upon breaching the true subterranean granite vault, the chamber prints the cryptographic handover vector that couples the bedrock survey with the final optical seal calculations. Transcribe the exact 64-hexadecimal handover vector recovered from within the authentic chamber.*
- **Answer:** `83687190e2798db9283c55e0658ac7eb262a51b185dd5ea44987380108f4317a`

---

#### Question 9
*To protect the station against unauthorized tampering and verify human operator presence, an official notice was placed across the root communications and usage screens. What is the sovereign canary token embedded within the Human Operator Notice archive?*
- **Answer:** `PRAMBH{canary_87eefe3e}`

---

#### Question 10
*The memory-hard chains have settled, the phantom duplicate archives have been rejected, the optical plates have yielded their secrets to living human eyes, and the four consecrated inks have been gathered into harmony. Inscribe the complete, uncorrupted final title verified and ratified by the survey record desk—exact in capitalization, delimiters, and characters, byte-for-byte.*
- **Answer:** `PRAMBH{43560fb33c8d0924_de918c455c4b1d42_66cb77c72ed791a7_Y22RGQ_9NK3HT_9UJYNG}`

---

### Confidential Operator Notes
- **Direct Submission:** All ten questions use direct text-input verification.
- **Answer Masks:** Auto-generated in TryHackMe room editor; no hint field enabled.
- **Prose Restraint:** Never describe the inner structure of the final title in prose or documentation — *"four inks, one order"* remains the sole public hint.
- **Distribution Archive:** The public artifact is `prambh.zip.enc` with SHA-256 manifest. The Keeper's 4-station perimeter landmark riddle holds the key (`gate hearth zinc field`).

