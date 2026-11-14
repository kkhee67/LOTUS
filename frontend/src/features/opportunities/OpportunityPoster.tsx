import {useState} from 'react';
import type {Opportunity} from '../../api';
import posters from './posters.json';
import banners from './banners.json';
import {sourceHref} from '../recommendations/presentation';

const verified: Record<string, {source: string; original: string}> = posters;

export function OpportunityPoster({item, label}: {item: Opportunity; label: string}) {
  const [failed, setFailed] = useState(false);
  const [bannerFailed, setBannerFailed] = useState(false);
  const source = item.source_kind === 'real' ? sourceHref(item.source_url) : undefined;
  const host = source ? new URL(source).hostname : '';
  const parks = host === 'job.alio.go.kr' && item.organization === '국립공원공단';
  const bannerHost = parks ? 'www.knps.or.kr' : host;
  const poster = verified[item.id];
  if (poster && item.source_kind === 'real' && poster.source === item.source_url && !failed) {
    return <div className="op-poster official">
      <img src={import.meta.env.BASE_URL + 'posters/' + item.id + '.webp'} alt="" loading="lazy"
        onError={() => setFailed(true)} />
    </div>;
  }
  if (source && Object.hasOwn(banners, bannerHost) && !bannerFailed) {
    return <div className="op-poster official site-banner">
      <img className={['donga.ac.kr', 'ot.konyang.ac.kr', 'www.q-net.or.kr', 'volunteer.2027chungcheong.com'].includes(bannerHost) ? 'dark-mat' : ''}
        src={import.meta.env.BASE_URL + 'source-banners/' + bannerHost + '.webp'} alt=""
        loading="lazy" onError={() => setBannerFailed(true)} />
    </div>;
  }
  return <div aria-hidden="true" className={'op-poster cover cover-' + item.type}>
    <small>LOTUS 안내 카드</small><span>{label}</span>
    <strong>{item.title}</strong><small>{item.organization}</small>
  </div>;
}
