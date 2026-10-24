import { Link, Navigate, useParams } from "react-router-dom";
import Disclaimer from "../components/Disclaimer";
import { useI18n } from "../i18n";
import { getBlogPost, listBlogPosts } from "../lib/blogPosts";
import { BLOG_BYLINE, LEGAL_ENTITY, PRODUCT_NAME } from "../lib/legal";

export default function BlogPostPage() {
  const { t } = useI18n();
  const { slug = "" } = useParams();
  const post = getBlogPost(slug);

  if (!post) {
    return <Navigate to="/blog" replace />;
  }

  const others = listBlogPosts()
    .filter((p) => p.slug !== post.slug)
    .slice(0, 4);

  return (
    <article className="blog-page blog-post" data-testid="blog-post">
      <p className="page-kicker">
        <Link to="/blog">{t("ui.BlogIndexPage.kicker")}</Link>
      </p>
      <header className="blog-post-header">
        <h1>{post.title}</h1>
        <p className="blog-meta">
          <span className="blog-byline">{BLOG_BYLINE}</span>
          {" · "}
          <time dateTime={post.published}>{post.published}</time>
          {post.updated && post.updated !== post.published ? (
            <>
              {" · "}
              <time dateTime={post.updated}>{t("ui.BlogPostPage.updated", { date: post.updated })}</time>
            </>
          ) : null}
          {" · "}
          {t("ui.BlogPostPage.minRead", { n: post.readingMinutes })}
          {" · "}
          {post.tags.join(" · ")}
        </p>
        <p className="muted lede">{post.description}</p>
      </header>
      <Disclaimer />
      <div className="blog-body">
        {post.sections.map((section, i) => (
          <section key={i} className="blog-section">
            {section.heading && <h2>{section.heading}</h2>}
            {section.paragraphs.map((p, j) => (
              <p key={j}>{p}</p>
            ))}
          </section>
        ))}
      </div>
      <footer className="blog-post-footer panel">
        <p>
          {t("ui.BlogPostPage.footer", { product: PRODUCT_NAME, entity: LEGAL_ENTITY })}
        </p>
        <div className="about-cta-row">
          <Link to="/tracker" className="btn primary">
            {t("ui.BlogPostPage.openTracker")}
          </Link>
          <Link to="/products#plans" className="btn">
            {t("ui.BlogPostPage.packagePricing")}
          </Link>
          <Link to="/blog" className="btn ghost">
            {t("ui.BlogPostPage.allArticles")}
          </Link>
        </div>
      </footer>
      {others.length > 0 && (
        <aside className="blog-related">
          <h2>{t("ui.BlogPostPage.more")}</h2>
          <ul>
            {others.map((p) => (
              <li key={p.slug}>
                <Link to={`/blog/${p.slug}`}>{p.title}</Link>
              </li>
            ))}
          </ul>
        </aside>
      )}
    </article>
  );
}
