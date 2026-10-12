<?php
/**
 * Plugin Name: Bernalier pSEO Pages
 * Description: Registers the programmatic SEO custom post type for BernalierPups.com. Direct port of MGR pSEO Pages (mgr-pseo-pages.php) — pages inherit the active theme automatically and are pushed in by the external generation engine via REST.
 * Version: 1.0
 * Author: A-WEB Marketing
 *
 * NOTE ON URL STRUCTURE: the mgr-pseo-engine repo's checked-in PHP has
 * rewrite slug '' (root), but the LIVE minigoldenretrievers.com site
 * actually serves engine pages at /guide/slug/ (verified via REST on
 * 2026-09-24 — e.g. /guide/mini-golden-retriever-puppy-price-texas/).
 * So the live plugin differs from what's in git. This Bernalier version
 * matches the LIVE behavior (/guide/slug/) since that's the pattern that
 * actually works in production. Change BERNALIER_CPT_SLUG below if a
 * different prefix is wanted.
 */

if (!defined('ABSPATH')) exit;

define('BERNALIER_CPT_SLUG', 'guide'); // -> bernalierpups.com/guide/slug/

add_action('init', function () {
    register_post_type('bernalier_page', [
        'labels' => [
            'name'          => 'Bernalier Pages',
            'singular_name' => 'Bernalier Page',
            'add_new_item'  => 'Add New Bernalier Page',
            'edit_item'     => 'Edit Bernalier Page',
        ],
        'public'       => true,
        'has_archive'  => false,
        'show_ui'      => true,
        'show_in_rest' => true,                       // REQUIRED for REST push
        'rest_base'    => 'bernalier_page',
        'menu_icon'    => 'dashicons-pets',
        'supports'     => ['title', 'editor', 'excerpt', 'custom-fields', 'thumbnail'],
        'rewrite'      => ['slug' => BERNALIER_CPT_SLUG, 'with_front' => false],
    ]);
});

/**
 * Register custom REST meta fields so the engine can set SEO title,
 * meta description, schema JSON, and intent/location tags.
 */
add_action('init', function () {
    foreach (['bernalier_seo_title', 'bernalier_meta_desc', 'bernalier_schema', 'bernalier_intent', 'bernalier_location'] as $key) {
        register_post_meta('bernalier_page', $key, [
            'show_in_rest' => true,
            'single'       => true,
            'type'         => 'string',
            'auth_callback'=> function () { return current_user_can('edit_posts'); },
        ]);
    }
});

/**
 * Output SEO meta + schema in <head> for bernalier_page singles.
 * NOTE: This site has Rank Math active (unlike MGR). If Rank Math also
 * outputs its own title/description tags for this CPT, you may get a
 * duplicate meta description tag — check the rendered <head> after
 * activating and either let Rank Math own it (disable this hook) or
 * exclude this CPT from Rank Math's own meta output. Not an issue on
 * MGR, which doesn't run Rank Math.
 */
add_action('wp_head', function () {
    if (!is_singular('bernalier_page')) return;
    $id     = get_the_ID();
    $desc   = get_post_meta($id, 'bernalier_meta_desc', true);
    $title  = get_post_meta($id, 'bernalier_seo_title', true);
    $schema = get_post_meta($id, 'bernalier_schema', true);
    if ($desc)   echo '<meta name="description" content="' . esc_attr($desc) . '">' . "\n";
    if ($title)  echo '<meta property="og:title" content="' . esc_attr($title) . '">' . "\n";
    if ($schema) echo '<script type="application/ld+json">' . $schema . '</script>' . "\n";
}, 1);

add_filter('document_title_parts', function ($parts) {
    if (is_singular('bernalier_page')) {
        $t = get_post_meta(get_the_ID(), 'bernalier_seo_title', true);
        if ($t) $parts['title'] = $t;
    }
    return $parts;
});

register_activation_hook(__FILE__, function () {
    flush_rewrite_rules();
});
register_deactivation_hook(__FILE__, function () {
    flush_rewrite_rules();
});

/**
 * Make sure Rank Math treats this CPT like any other public content type
 * for sitemaps (auto-detects public+show_in_rest CPTs, this is a safety net).
 */
add_filter('rank_math/sitemap/post_types', function ($post_types) {
    if (!in_array('bernalier_page', $post_types, true)) {
        $post_types[] = 'bernalier_page';
    }
    return $post_types;
});
