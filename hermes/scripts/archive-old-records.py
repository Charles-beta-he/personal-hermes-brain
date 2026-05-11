#!/usr/bin/env python3
"""
Archive Old Records — 压缩 30 天前的 health history
用法: python3 archive-old-records.py [--dry-run]
"""
import os, sys, json, datetime, gzip

HEALTH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/health-history.jsonl")
ARCHIVE_DIR = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/archives")
CUTOFF_DAYS = 30

def main():
    dry_run = "--dry-run" in sys.argv
    
    if not os.path.exists(HEALTH):
        print("No health history found")
        return
    
    cutoff = datetime.datetime.now() - datetime.timedelta(days=CUTOFF_DAYS)
    
    keep = []
    archive = []
    
    with open(HEALTH) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                ts = datetime.datetime.fromisoformat(rec["timestamp"])
                if ts > cutoff:
                    keep.append(line)
                else:
                    archive.append(line)
            except:
                keep.append(line)
    
    if not archive:
        print("No old records to archive")
        return
    
    print(f"Records: keep={len(keep)}, archive={len(archive)}")
    
    if dry_run:
        print("(dry-run, no changes made)")
        return
    
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    # 写入归档文件 (gzip)
    archive_file = os.path.join(ARCHIVE_DIR, f"health-{cutoff.year}{cutoff.month:02d}.jsonl.gz")
    with gzip.open(archive_file, "wt") as f:
        f.writelines(archive)
    
    # 重写 health-history (只保留近期)
    with open(HEALTH, "w") as f:
        f.writelines(keep)
    
    print(f"Archived to: {archive_file}")
    print(f"Compressed: {len(archive)} records")

if __name__ == "__main__":
    main()
