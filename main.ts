import {
  getTrendingMoviesPuppeteer,
  getStreamLinksFromWatchPage,
  resolveM3U8FromEmbed,
} from './scraper/nunflix-puppeteer';

import { exportToM3U, M3UItem } from './export';

(async () => {
  const movies = await getTrendingMoviesPuppeteer();
  const items: M3UItem[] = [];

  for (const movie of movies.slice(0, 5)) {
    console.log(`\n🎬 ${movie.title}`);
    console.log(`Watch page: ${movie.watchPage}`);

    const embedLinks = await getStreamLinksFromWatchPage(movie.watchPage);

    for (const embed of embedLinks) {
      console.log(`\n🧩 Trying server: ${embed}`);
      const m3u8 = await resolveM3U8FromEmbed(embed);

      if (m3u8) {
        console.log(`✅ Found .m3u8: ${m3u8}`);

        items.push({
          title: movie.title,
          logo: movie.poster || '',
          group: 'Movies',
          streamUrl: m3u8,
          description: '', // Optionally fill with IMDb or year
        });

        break; // Stop after first working stream
      } else {
        console.log('❌ No .m3u8 found.');
      }
    }
  }

  if (items.length > 0) {
    exportToM3U('movies&tvshows.m3u', items);
  } else {
    console.log('⚠️ No playable streams found to export.');
  }
})();
