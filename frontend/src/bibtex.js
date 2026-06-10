// BibTeX generation — mirror of backend/citations.py (keep both in sync).
// Runs client-side so "Cite" works instantly from data already in memory.

export function formatAuthors(authorsStr) {
    // "First Last, First M Last" -> "Last, First and Last, First M"
    if (!authorsStr) return '';
    return authorsStr.split(',')
        .map(s => s.trim())
        .filter(Boolean)
        .map(name => {
            const parts = name.split(/\s+/);
            if (parts.length === 1) return parts[0];
            const family = parts[parts.length - 1];
            const given = parts.slice(0, -1).join(' ');
            return `${family}, ${given}`;
        })
        .join(' and ');
}

export function citeKey(paper) {
    const authors = paper.authors || '';
    const first = authors ? authors.split(',')[0].trim() : '';
    const family = first ? first.split(/\s+/).pop() : '';
    const year = paper.year || '';
    const key = `${family}${year}`.replace(/[^A-Za-z0-9]/g, '');
    return key || paper.id || 'ref';
}

export function bibtex(paper) {
    const key = citeKey(paper);
    const title = paper.title || 'Untitled';
    const authors = formatAuthors(paper.authors || '');
    const year = paper.year || '';
    const doi = paper.doi || '';
    const venue = paper.venue || '';
    const oaid = paper.id || '';

    const fields = [`  title = {${title}}`];
    if (authors) fields.push(`  author = {${authors}}`);
    if (year) fields.push(`  year = {${year}}`);

    let entry;
    if (venue) {
        entry = 'article';
        fields.push(`  journal = {${venue}}`);
    } else {
        entry = 'misc';
        if (oaid) fields.push(`  howpublished = {\\url{https://openalex.org/${oaid}}}`);
    }
    if (doi) fields.push(`  doi = {${doi}}`);
    if (oaid && entry === 'misc') fields.push(`  note = {OpenAlex: ${oaid}}`);

    return `@${entry}{${key},\n${fields.join(',\n')}\n}`;
}

export function bibtexForMany(papers) {
    return papers.map(bibtex).join('\n\n');
}
