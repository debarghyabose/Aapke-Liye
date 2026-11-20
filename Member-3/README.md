# 🤖 Member 3: AI Engineer

**Name:** _your name_ · **GitHub:** _@handle_

## Your job
All the Google AI: turn a citizen's voice into a claim, ask follow-up questions out loud, check proof photos, and recheck offline claims on the server.

## Workflow steps you own
| Step | What |
|---|---|
| 3 | **Gemini:** voice → claim JSON |
| ◇ | **Fields missing?** Detect what's still needed |
| 4 | Gemini writes a follow-up question; **Cloud TTS** speaks it |
| 5 | Cloud TTS read-back (online) |
| 6 | **Gemini vision** checks substitute proof |
| — | **Server recheck:** Gemini re-reads audio and photos of offline claims |

## Tasks
- [ ] Prompt that turns audio into claim JSON in the agreed format, never inventing facts
- [ ] Detect missing required fields
- [ ] Short, simple follow-up questions in all 6 languages
- [ ] Cloud TTS with a good voice per language; cache common phrases
- [ ] Vision check for substitute proof (what document is it, and is it readable?)
- [ ] Vision check on damage photos (does this look like disaster damage?)
- [ ] Server recheck of offline claims: compare the audio with the tapped answers, flag conflicts for review
- [ ] Test set of 30+ sample recordings across languages; track accuracy
- [ ] Fail fast with a clear error when AI is unavailable, so the phone falls back to the offline flow

## Timeline
| Week | Focus |
|---|---|
| 1 | Gemini audio → JSON prototype (Hindi + English) |
| 2 | Structured output, missing-field detection |
| 3 | Follow-up questions in 6 languages, Cloud TTS |
| 4 | Read-back speech, phrase cache, test set v1 |
| 5 | Vision proof check, server recheck of offline claims |
| 6 | Accuracy tuning on the test set |

## You work closely with
- **Member 1:** playing questions and recording answers
- **Member 4:** the voice API routes and where AI results are stored
- **Member 5:** prompting for the "Ask your claims" feature

## Done when
Voice → claim field accuracy is **≥ 90 %** on the test set across all 6 languages, and every offline claim is rechecked after it syncs.
