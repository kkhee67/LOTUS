import type {Opportunity} from '../../api';
import topics from '../../../../shared/search_topics.json' with {type: 'json'};

const normalize = (text: string) => text.normalize('NFKC').toLowerCase();
const groups = topics.map(topic => topic.map(normalize));

export function opportunitySearch(query: string) {
  const terms = normalize(query).trim().split(/\s+/).filter(Boolean).map(word => {
    const related = new Set(groups.filter(topic => word.length >= 2 && topic.some(alias => alias.startsWith(word))).flat());
    related.delete(word);
    // Generic development also describes land and business development.
    related.delete('개발');
    const patterns = [...related].map(term => {
      const literal = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      return new RegExp(/^[\x00-\x7F]+$/.test(term) ? '(?<![a-z0-9])' + literal + '(?![a-z0-9])' : literal);
    });
    return {word, patterns};
  });
  return (item: Opportunity) => {
    if (!terms.length) return true;
    const fields = [item.title, item.organization, item.summary, item.type, item.subtype ?? '',
      ...(item.tags ?? []), ...(item.fields ?? []), ...(item.activities ?? []),
      ...(item.related_majors ?? []), ...(item.requirements ?? [])].map(normalize);
    return terms.every(({word, patterns}) => fields.some(text => text.includes(word) || patterns.some(pattern => pattern.test(text))));
  };
}
