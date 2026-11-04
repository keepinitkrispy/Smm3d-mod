# CPU, renderer and compiler source audit — 2026-11-04

Read-only audit. No app/config/source changes; no measured FPS benefit claimed. Sources inspected in the active recomp workspace, with cap40/link.py and o2/link-runtime.py to identify build inputs. O2 metadata records -O2 -flto=thin and ID ff0e33f110679bd7. Source hashes accompany this report; not every source/object pair has been rebuilt or proven identical. In particular the workspace dispatch.c contains hot_split_install while the saved cap40 runtime symbol table does not: do not assume every current source edit is installed.

## Ranked candidates

1. **Over-conservative GPU dependency tracking** — runtime/nvn/vulkan/exec.c:2441 gfx_gmap copies guest storage into transient memory; :2904 stage_set nevertheless marks all 16 guest storage bindings for EACH storage descriptor. :449 gpu_read_mark marks 64 KiB pages. :4553 uniform updates and :4465 clears flush/wait if marked. In no-import, copy-only paths this can mark source data which GPU no longer reads, as well as unrelated bytes on the same page. Confirm all indirect/compute/writeback consumers before suppressing marks. Instrument flush count/time by reason, bytes actually read versus conservatively marked. Keep imported/direct-memory dependencies intact. This is a concrete code path and an unmeasured optimization hypothesis, not proof of the dominant stall.

2. **Storage-buffer staging bypasses existing reuse** — :2441 gfx_gmap sorts/merges bound ranges and memcpy's them into fresh transient spans for every applicable stage/draw. :617 guest_copy already caches other copies by submission plus write-generation. gfx_gmap doesn't use that cache. Share immutable snapshots within the same write-generation, with proper CPU/GPU write invalidation and buffer lifetime. Do not cache by address alone. Count repeated range sets and copy bytes first.

3. **Fresh descriptors every draw** — :2872 stage_set allocates a set, rebuilds descriptor writes and vkUpdateDescriptorSets; :3511 always binds new sets. Cache identical resolved descriptor contents/layout within pool/submission lifetime. Existing texture-view memo is NOT descriptor-set reuse. Dynamic buffer offsets and mutable uniforms must remain distinct. Existing prof_sets gives CPU timing for prioritization.

4. **Double pipeline-key work after warmup** — :4700 backend_prefetch walks command lists before execution; scan_draw at :4625 builds and hashes a pipeline key even for cached pipelines. draw_ at :3290 does it again (~700-byte key). Warm SPIR-V/pipeline caches do not remove the scanner. A separate generation-based pipeline-state cache can avoid rebuilding unchanged keys. A scan-disable experiment must preserve synchronous demand compilation; never use skip-draw async mode as an FPS optimization. The ahead.c worker and this prefetch scan are different mechanisms.

5. **Duplicate pending pipeline allocations** — scan_draw :4653 appends a PipeReq for each repeated key while a program is pending. pipe_requests_run :3119 allocates a Pipe for each request before pend_get_or_put deduplicates it, then frees duplicates. Deduplicate requests before allocation by complete key/hash with collision handling. Most relevant at compilation/scene entry, not established as steady-state work.

6. **Global scheduler instrumentation** — kernel.c:119 core_refresh_preempt scans all threads and globally enables FN_ENTER on any waiting core. fnprof.c:73 calls safepoint for instrumented function entries; kernel.c:202 every 32 entries takes the global lock and scans waiters even when contention belongs to another core. Maintain per-core waiter/priority summaries and gate on the current guest core, keeping exclusive ownership and fairness. Do not simply disable preemption or remove locks. Earlier core-local experiments exist; compare them before implementation.

7. **No-import zero-buffer churn** — exec.c:2397 gmem_info uploads 4096 zero bytes every fallback descriptor request. With no import, device.c disables BDA, so this fallback is returned directly. Reuse a properly initialized immutable zero buffer or per-submission span instead. Savings depend on number of descriptors using this binding; measure calls and bytes. There is no reason to import the full guest heap for this.

8. **Host allocation and retained memory** — non-native index topologies allocate expand_indices output, copy it to the transient ring, then free it (:3530/:3560). Generate directly into a reserved span or reuse scratch. Transient chunks are 64 MiB (:516); they recycle but do not shrink in the inspected path. This is high-water retention, not automatically a leak or a reason to shrink blindly. Track chunk count/high-water and wait pressure. Texture destruction queue requires creation/reuse counters before blaming it for system dmabuf CPU.

## Compiler audit

- Game artifact: ~/smm2-hot/o2/recomp/build/smm2-android-arm64-0x800000000/libsmm2game.so. .text size 0x802b938 = about 128.17 MiB. llvm-size text category is 147344987 bytes including read-only sections, not all executable instructions.
- Largest named functions include f_8016aac20 size 0xb1d50 (728400 bytes) and f_8016c2c70 size 0xa305c (667740 bytes). Prior split64 variants exist separately; these symbols remain large in O2. Code size alone does not prove they are hot.
- Saved generated code uses Cpu-register loads/stores and FN_ENTER per guest function. Calls across the game/runtime shared-library boundary limit whole-program optimization. ThinLTO of the game does not optimize runtime internals across that boundary.
- cap40 link script reuses 243 objects, replacing gamelib/dispatch/device only. Inspected Vulkan exec.o is native ELF machine code with .text, not LLVM bitcode; that renderer object cannot receive ThinLTO at final link. Runtime source Makefile defaults to -O2. A consistent runtime ThinLTO rebuild is a candidate, not a proven speedup.
- Recorded game flags have no explicit CPU tuning or profile-guided feedback. Prioritize measured hot functions/dispatch misses and instruction-cache behavior; then compare PGO/hot-cold layout, selective splitting or outlining and runtime ThinLTO. Avoid blanket -O3/unrolling that could enlarge hot code. Preserve -fno-strict-aliasing and guest floating-point semantics; removing them is not a safe generic optimization.
- dispatch.c cache indexes low PC bits into 4096 direct-mapped entries. Collision/miss rate is unknown; instrument it before testing a mixed hash or small set-associative cache. Do not apply workspace dispatch edits blindly: saved runtime provenance differs.

## Already present / lower priority

Vertex copies have guest_copy reuse; texture views have per-frame memoization; texture uploads have write-watch/hash checks; shader compilation workers already limited to two on Android; job queues already block on condition variables. Avoid proposing these as missing features. Audio still polls at 1 ms and display queries still need separate inspection against the latest cap patch, but those were already identified leads.

## First measurements

On verified O2, same playable scene: existing LARECOMP_VK_PROF timing for sets/key/vertex/submit; add flush-by-reason and staged-range reuse counters. Measure scheduler hook invocations and current-core/no-current-core waiter outcomes. Gather function samples with a profileable APK. Test one change at a time; acceptance remains FPS at 150–180 seconds plus input/audio/rendering correctness. No thermal status override.
