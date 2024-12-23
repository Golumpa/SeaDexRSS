import json
from datetime import timezone

from feedgen.feed import FeedGenerator


def format_comparison_links(comparison):
    if not comparison:
        return "N/A"

    if isinstance(comparison, str):
        urls = comparison.split(",")
    elif isinstance(comparison, list):
        urls = comparison
    else:
        return "N/A"

    links = []
    for i, url in enumerate(urls, 1):
        links.append(f'<a href="{url.strip()}">Comparison {i}</a>')

    return " | ".join(links)


def format_snapshot_data(snapshot):
    try:
        data = json.loads(snapshot.data)
    except json.JSONDecodeError:
        return f"Error: Unable to parse snapshot data for Anilist ID {snapshot.anilist_id}"

    formatted_output = f"""
<img src="{snapshot.cover_image_url}" alt="{snapshot.anime_title}" style="float: left; margin-right: 10px;"/>
<h2>There has been an update for the SeaDex entry for {snapshot.anime_title}.</h2>
<p>Below is the latest version of the SeaDex entry.</p>
<br>
<ul>
    <li><strong>Updated:</strong> {data.get('updated', 'N/A')}</li>
    <li><strong>Comparison:</strong> {format_comparison_links(data.get('comparison'))}</li>
    <li><strong>Complete?:</strong> <span style="color: {'green' if not data.get('incomplete', True) else 'red'};">{not data.get('incomplete', True)}</span></li>
    <br>
    <li><strong>Notes:</strong> {data.get('notes', 'N/A')}</li>
</ul>
<div style="clear: both">
<br>
<h3><strong>Torrents:</strong></h3>
</div>
<br>
"""
    for torrent in data.get("expand", {}).get("trs", []):
        total_size_gib = sum(file.get("length", 0) for file in torrent.get("files", [])) / (1024**3)
        formatted_output += f"""
<h4><u>{torrent.get('releaseGroup', 'Unknown Group')}</u></h4>
<ul>
    <li><strong>Size:</strong> {total_size_gib:.2f} GiB</li>
    <li><strong>Is Best?:</strong> <span style="color: {'green' if torrent.get('isBest') else 'red'};">{torrent.get('isBest', 'No')}</span></li>
    <li><strong>Dual Audio?:</strong> <span style="color: {'green' if torrent.get('dualAudio') else 'red'};">{torrent.get('dualAudio', 'No')}</span></li>
    <li><strong>Tracker:</strong> {torrent.get('tracker', 'N/A')}</li>
    <li><strong>Torrent Url:</strong> <a href="{torrent.get('url', '#')}">Link</a></li>
</ul>
<br>
"""
    return formatted_output


def generate_rss(snapshots, anilist_id):
    fg = FeedGenerator()

    anime_title = snapshots[0].anime_title if snapshots else f"Anilist ID {anilist_id}"

    fg.title(f"Seadex Updates for {anime_title}")
    fg.link(href=f"https://releases.moe/{anilist_id}/", rel="alternate")
    fg.description(f"Seadex updates for {anime_title} (Anilist ID: {anilist_id})")

    for snapshot in snapshots:
        fe = fg.add_entry()
        formatted_date = snapshot.timestamp.strftime("%d/%m/%Y")
        fe.title(f"Update on {formatted_date}")
        fe.link(href=f"https://anilist.co/anime/{anilist_id}")

        formatted_data = format_snapshot_data(snapshot)
        fe.description(formatted_data)

        if snapshot.timestamp.tzinfo is None:
            timestamp = snapshot.timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = snapshot.timestamp

        fe.pubDate(timestamp)

    return fg.rss_str(pretty=True)
