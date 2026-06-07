# $XBRDG Post Archive

One directory per day. Each post is its own file — slot, status, copy, media note.

## Structure

```
posts/
  day-01-march-18/    ← launch day
  day-02-march-19/    ← current
    schedule.md       ← full day overview + media checklist
    post-HHMM-slug.md ← individual posts, named by UTC slot
```

## File Format

Each post file contains:
- Slot (UTC time)
- Status (READY / POSTED / SKIP)
- Media note (which asset to attach)
- Copy (copy-paste ready)
- Hashtags

## Adding New Days

```
mkdir posts/day-03-march-20
```

Then create `schedule.md` + individual post files.
Update status to `POSTED` after publishing so the archive stays clean.
