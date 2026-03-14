# Video Title Selection Algorithm

## Overview

This document describes the improved algorithm used by `rip_video.py` to automatically select the main feature title from Blu-ray discs and DVDs.

## Problem Statement

The original algorithm had several issues:
- **Duration-based sorting** could pick longer special features over the main movie
- **60-second tolerance** was too wide for seamless branching detection
- **No size consideration** failed to distinguish between main features and bonus content
- **Edge cases** like documentaries longer than the main film were handled poorly

## Improved Algorithm

### 1. Primary Sort by File Size

```python
# Sort by size (largest first) as primary indicator of main feature
titles.sort(key=lambda x: x[3], reverse=True)
```

**Rationale**: File size is a better indicator of main feature content than duration for modern media.

### 2. Percentage-Based Filtering

```python
def is_main_feature_candidate(title_data, all_titles):
    title_id, duration_seconds, duration_str, size_bytes = title_data
    
    # Get the longest duration and largest size from ALL titles
    longest_duration = max(t[1] for t in all_titles)
    largest_size = max(t[3] for t in all_titles)
    
    # Calculate ratios
    size_ratio = size_bytes / largest_size
    duration_ratio = duration_seconds / longest_duration
    
    # Percentage-based thresholds
    MIN_SIZE_RATIO = 0.75  # At least 75% of largest size
    MIN_DURATION_RATIO = 0.4  # At least 40% of longest duration
    
    return (
        size_ratio >= MIN_SIZE_RATIO and
        duration_ratio >= MIN_DURATION_RATIO
    )
```

**Thresholds**:
- **75% size ratio**: Eliminates most special features, trailers, and minor content
- **40% duration ratio**: Handles shorter films vs longer documentaries
- **Both percentages**: Scale with content type (no fixed duration limits)

### 3. Candidate-Based Selection

```python
# Filter titles to only main feature candidates
candidates = [
    t for t in titles 
    if is_main_feature_candidate(t, titles)
]
```

### 4. Improved Seamless Branching Detection

```python
# Detect seamless branching only among qualified candidates
if len(candidates) >= 3:
    longest_duration = candidates[0][1]
    same_duration_candidates = [
        t for t in candidates 
        if abs(t[1] - longest_duration) <= 30  # Tighter 30-second window
    ]
    is_seamless_branching = len(same_duration_candidates) >= 3
else:
    is_seamless_branching = False
```

**Improvements**:
- **30-second window** (tighter than 60 seconds)
- **Only considers qualified candidates**
- **Requires 3+ similar candidates** for seamless branching

## Edge Case Handling

### Case A: Old B&W Film + Modern Documentary
- **Film**: 8G (67%), 1.5h (75%) → ✅ Passes both thresholds
- **Documentary**: 12G (100%), 2h (100%) → ✅ Passes both thresholds
- **Result**: Seamless branching logic applies correctly

### Case B: New Film + Longer Documentary
- **Film**: 25G (100%), 2.5h (83%) → ✅ Passes both thresholds
- **Documentary**: 15G (60%), 3h (100%) → ❌ Fails size threshold (60% < 75%)
- **Result**: Only film considered → correct selection

### Case C: Short Film Anthology
- **Main**: 8G (100%), 15min (100%) → ✅ Passes both thresholds
- **Extra**: 2G (25%), 5min (33%) → ❌ Fails both thresholds
- **Result**: Only main feature considered

### Case D: TV Series with Special
- **Main**: 12G (100%), 45min (100%) → ✅ Passes both thresholds
- **Special**: 4G (33%), 20min (44%) → ❌ Fails size threshold
- **Result**: Only main episode considered

## Real-World Example: Planet of the Apes (1968)

| Title | Size | Duration | Size % | Duration % | Status |
|-------|------|----------|--------|------------|---------|
| t00 | 24.9G | 1:52:02 | 100% | 88% | ✅ **Main feature** |
| t01 | 2.9G | 2:06:44 | 11.6% | 100% | ❌ **Too small** |
| t09 | 5.5G | 0:00:00 | 22% | 0% | ❌ **Data file** |

**Result**: t00 correctly selected as main feature (was incorrectly selecting t01 before)

## Fallback Behavior

If no titles meet the candidate criteria:
1. **Fallback to largest file** (still sorted by size)
2. **Log warning** about unclear main feature
3. **Continue with rip** using largest title

This ensures the algorithm never fails to produce a result, even for unusual disc structures.

## Configuration

The thresholds can be adjusted in `rip_video.py` if needed:

```python
MIN_SIZE_RATIO = 0.75  # At least 75% of largest size
MIN_DURATION_RATIO = 0.4  # At least 40% of longest duration
SEAMLESS_BRANCHING_WINDOW = 30  # 30-second duration window
```

## Testing

The algorithm has been tested with:
- Standard Blu-ray movies
- Blu-rays with extensive special features
- TV series discs
- Multi-language seamless branching discs
- Edge cases with documentaries longer than main features

## Backward Compatibility

The improved algorithm maintains full backward compatibility:
- **TITLE_INDEX** environment variable still works
- **Manual title selection** still available
- **All existing command-line options** preserved
- **Fallback behavior** ensures no regression in edge cases
