/*
 * This file Copyright (C) Mnemosyne LLC
 *
 * This file is licensed by the GPL version 2. Works owned by the
 * Transmission project are granted a special exemption to clause 2(b)
 * so that the bulk of its code can remain under the MIT license.
 * This exemption does not extend to derived works not owned by
 * the Transmission project.
 *
 * $Id: torrent-cell-renderer.c 11747 2011-01-22 13:26:44Z jordan $
 */

#include <string.h> /* strcmp() */
#include <gtk/gtk.h>
#include <glib/gi18n.h>
#include <libtransmission/transmission.h>
#include <libtransmission/utils.h> /* tr_truncd() */
#include "hig.h"
#include "icons.h"
#include "torrent-cell-renderer.h"
#include "tr-torrent.h"
#include "util.h"

/* #define TEST_RTL */

enum
{
    P_TORRENT = 1,
    P_UPLOAD_SPEED,
    P_DOWNLOAD_SPEED,
    P_BAR_HEIGHT,
    P_COMPACT
};

#define DEFAULT_BAR_HEIGHT 12
#define SMALL_SCALE 0.9
#define COMPACT_ICON_SIZE GTK_ICON_SIZE_MENU
#define FULL_ICON_SIZE GTK_ICON_SIZE_DND

/***
****
***/

static char*
getProgressString( const tr_torrent * tor,
                   const tr_info    * info,
                   const tr_stat    * st )
{
    const int      isDone = st->leftUntilDone == 0;
    const uint64_t haveTotal = st->haveUnchecked + st->haveValid;
    const int      isSeed = st->haveValid >= info->totalSize;
    char           buf1[32], buf2[32], buf3[32], buf4[32], buf5[32], buf6[32];
    char *         str;
    double         seedRatio;
    const gboolean hasSeedRatio = tr_torrentGetSeedRatio( tor, &seedRatio );

    if( !isDone ) /* downloading */
    {
        str = g_strdup_printf(
            /* %1$s is how much we've got,
               %2$s is how much we'll have when done,
               %3$s%% is a percentage of the two */
            _( "%1$s of %2$s (%3$s%%)" ),
            tr_strlsize( buf1, haveTotal, sizeof( buf1 ) ),
            tr_strlsize( buf2, st->sizeWhenDone, sizeof( buf2 ) ),
            tr_strlpercent( buf3, st->percentDone * 100.0, sizeof( buf3 ) ) );
    }
    else if( !isSeed ) /* partial seeds */
    {
        if( hasSeedRatio )
        {
            str = g_strdup_printf(
                /* %1$s is how much we've got,
                   %2$s is the torrent's total size,
                   %3$s%% is a percentage of the two,
                   %4$s is how much we've uploaded,
                   %5$s is our upload-to-download ratio,
                   %6$s is the ratio we want to reach before we stop uploading */
                _( "%1$s of %2$s (%3$s%%), uploaded %4$s (Ratio: %5$s Goal: %6$s)" ),
                tr_strlsize( buf1, haveTotal, sizeof( buf1 ) ),
                tr_strlsize( buf2, info->totalSize, sizeof( buf2 ) ),
                tr_strlpercent( buf3, st->percentComplete * 100.0, sizeof( buf3 ) ),
                tr_strlsize( buf4, st->uploadedEver, sizeof( buf4 ) ),
                tr_strlratio( buf5, st->ratio, sizeof( buf5 ) ),
                tr_strlratio( buf6, seedRatio, sizeof( buf6 ) ) );
        }
        else
        {
            str = g_strdup_printf(
                /* %1$s is how much we've got,
                   %2$s is the torrent's total size,
                   %3$s%% is a percentage of the two,
                   %4$s is how much we've uploaded,
                   %5$s is our upload-to-download ratio */
                _( "%1$s of %2$s (%3$s%%), uploaded %4$s (Ratio: %5$s)" ),
                tr_strlsize( buf1, haveTotal, sizeof( buf1 ) ),
                tr_strlsize( buf2, info->totalSize, sizeof( buf2 ) ),
                tr_strlpercent( buf3, st->percentComplete * 100.0, sizeof( buf3 ) ),
                tr_strlsize( buf4, st->uploadedEver, sizeof( buf4 ) ),
                tr_strlratio( buf5, st->ratio, sizeof( buf5 ) ) );
        }
    }
    else /* seeding */
    {
        if( hasSeedRatio )
        {
            str = g_strdup_printf(
                /* %1$s is the torrent's total size,
                   %2$s is how much we've uploaded,
                   %3$s is our upload-to-download ratio,
                   %4$s is the ratio we want to reach before we stop uploading */
                _( "%1$s, uploaded %2$s (Ratio: %3$s Goal: %4$s)" ),
                tr_strlsize( buf1, info->totalSize, sizeof( buf1 ) ),
                tr_strlsize( buf2, st->uploadedEver, sizeof( buf2 ) ),
                tr_strlratio( buf3, st->ratio, sizeof( buf3 ) ),
                tr_strlratio( buf4, seedRatio, sizeof( buf4 ) ) );
        }
        else /* seeding w/o a ratio */
        {
            str = g_strdup_printf(
                /* %1$s is the torrent's total size,
                   %2$s is how much we've uploaded,
                   %3$s is our upload-to-download ratio */
                _( "%1$s, uploaded %2$s (Ratio: %3$s)" ),
                tr_strlsize( buf1, info->totalSize, sizeof( buf1 ) ),
                tr_strlsize( buf2, st->uploadedEver, sizeof( buf2 ) ),
                tr_strlratio( buf3, st->ratio, sizeof( buf3 ) ) );
        }
    }

    /* add time when downloading */
    if( ( st->activity == TR_STATUS_DOWNLOAD )
        || ( hasSeedRatio && ( st->activity == TR_STATUS_SEED ) ) )
    {
        const int eta = st->eta;
        GString * gstr = g_string_new( str );
        g_string_append( gstr, " - " );
        if( eta < 0 )
            g_string_append( gstr, _( "Remaining time unknown" ) );
        else
        {
            char timestr[128];
            tr_strltime( timestr, eta, sizeof( timestr ) );
            /* time remaining */
            g_string_append_printf( gstr, _( "%s remaining" ), timestr );
        }
        g_free( str );
        str = g_string_free( gstr, FALSE );
    }

    return str;
}

static char*
getShortTransferString( const tr_torrent  * tor,
                        const tr_stat     * st,
                        double              uploadSpeed_KBps,
                        double              downloadSpeed_KBps,
                        char              * buf,
                        size_t              buflen )
{
    char downStr[32], upStr[32];
    const int haveMeta = tr_torrentHasMetadata( tor );
    const int haveUp = haveMeta && st->peersGettingFromUs > 0;
    const int haveDown = haveMeta && ( ( st->peersSendingToUs > 0 ) || ( st->webseedsSendingToUs > 0 ) );

    if( haveDown )
        tr_formatter_speed_KBps( downStr, downloadSpeed_KBps, sizeof( downStr ) );
    if( haveUp )
        tr_formatter_speed_KBps( upStr, uploadSpeed_KBps, sizeof( upStr ) );

    if( haveDown && haveUp )
        /* 1==down arrow, 2==down speed, 3==up arrow, 4==down speed */
        g_snprintf( buf, buflen, _( "%1$s %2$s, %3$s %4$s" ),
                    gtr_get_unicode_string( GTR_UNICODE_DOWN ), downStr,
                    gtr_get_unicode_string( GTR_UNICODE_UP ), upStr );
    else if( haveDown )
        /* bandwidth speed + unicode arrow */
        g_snprintf( buf, buflen, _( "%1$s %2$s" ),
                    gtr_get_unicode_string( GTR_UNICODE_DOWN ), downStr );
    else if( haveUp )
        /* bandwidth speed + unicode arrow */
        g_snprintf( buf, buflen, _( "%1$s %2$s" ),
                    gtr_get_unicode_string( GTR_UNICODE_UP ), upStr );
    else if( haveMeta )
        /* the torrent isn't uploading or downloading */
        g_strlcpy( buf, _( "Idle" ), buflen );
    else
        *buf = '\0';

    return buf;
}

static char*
getShortStatusString( const tr_torrent  * tor,
                      const tr_stat     * st,
                      double              uploadSpeed_KBps,
                      double              downloadSpeed_KBps )
{
    GString * gstr = g_string_new( NULL );

    switch( st->activity )
    {
        case TR_STATUS_STOPPED:
            if( st->finished )
                g_string_assign( gstr, _( "Finished" ) );
            else
                g_string_assign( gstr, _( "Paused" ) );
            break;

        case TR_STATUS_CHECK_WAIT:
            g_string_assign( gstr, _( "Waiting to verify local data" ) );
            break;

        case TR_STATUS_CHECK:
            g_string_append_printf( gstr,
                                    _( "Verifying local data (%.1f%% tested)" ),
                                    tr_truncd( st->recheckProgress * 100.0, 1 ) );
            break;

        case TR_STATUS_DOWNLOAD:
        case TR_STATUS_SEED:
        {
            char buf[512];
            if( st->activity != TR_STATUS_DOWNLOAD )
            {
                tr_strlratio( buf, st->ratio, sizeof( buf ) );
                g_string_append_printf( gstr, _( "Ratio %s" ), buf );
                g_string_append( gstr, ", " );
            }
            getShortTransferString( tor, st, uploadSpeed_KBps, downloadSpeed_KBps, buf, sizeof( buf ) );
            g_string_append( gstr, buf );
            break;
        }

        default:
            break;
    }

    return g_string_free( gstr, FALSE );
}

static char*
getStatusString( const tr_torrent  * tor,
                 const tr_stat     * st,
                 const double        uploadSpeed_KBps,
                 const double        downloadSpeed_KBps )
{
    const int isActive = st->activity != TR_STATUS_STOPPED;
    const int isChecking = st->activity == TR_STATUS_CHECK
                        || st->activity == TR_STATUS_CHECK_WAIT;

    GString * gstr = g_string_new( NULL );

    if( st->error )
    {
        const char * fmt[] = { NULL, N_( "Tracker gave a warning: \"%s\"" ),
                                     N_( "Tracker gave an error: \"%s\"" ),
                                     N_( "Error: %s" ) };
        g_string_append_printf( gstr, _( fmt[st->error] ), st->errorString );
    }
    else switch( st->activity )
    {
        case TR_STATUS_STOPPED:
        case TR_STATUS_CHECK_WAIT:
        case TR_STATUS_CHECK:
        {
            char * pch = getShortStatusString( tor, st, uploadSpeed_KBps, downloadSpeed_KBps );
            g_string_assign( gstr, pch );
            g_free( pch );
            break;
        }

        case TR_STATUS_DOWNLOAD:
        {
            if( tr_torrentHasMetadata( tor ) )
            {
                g_string_append_printf( gstr,
                    gtr_ngettext( "Downloading from %1$'d of %2$'d connected peer",
                                  "Downloading from %1$'d of %2$'d connected peers",
                                  st->webseedsSendingToUs + st->peersSendingToUs ),
                    st->webseedsSendingToUs + st->peersSendingToUs,
                    st->webseedsSendingToUs + st->peersConnected );
            }
            else
            {
                g_string_append_printf( gstr,
                    gtr_ngettext( "Downloading metadata from %1$'d peer (%2$d%% done)",
                                  "Downloading metadata from %1$'d peers (%2$d%% done)",
                                  st->peersConnected + st->peersConnected ),
                    st->peersConnected + st->webseedsSendingToUs,
                    (int)(100.0*st->metadataPercentComplete) );
            }
            break;
        }

        case TR_STATUS_SEED:
            g_string_append_printf( gstr,
                gtr_ngettext( "Seeding to %1$'d of %2$'d connected peer",
                              "Seeding to %1$'d of %2$'d connected peers",
                              st->peersConnected ),
                st->peersGettingFromUs,
                st->peersConnected );
                break;
    }

    if( isActive && !isChecking )
    {
        char buf[256];
        getShortTransferString( tor, st, uploadSpeed_KBps, downloadSpeed_KBps, buf, sizeof( buf ) );
        if( *buf )
            g_string_append_printf( gstr, " - %s", buf );
    }

    return g_string_free( gstr, FALSE );
}

/***
****
***/

static GtkCellRendererClass * parent_class = NULL;

struct TorrentCellRendererPrivate
{
    tr_torrent       * tor;
    GtkCellRenderer  * text_renderer;
    GtkCellRenderer  * progress_renderer;
    GtkCellRenderer  * icon_renderer;
    int bar_height;

    /* Use this instead of tr_stat.pieceUploadSpeed so that the model can
       control when the speed displays get updated. This is done to keep
       the individual torrents' speeds and the status bar's overall speed
       in sync even if they refresh at slightly different times */
    double upload_speed_KBps;

    /* @see upload_speed_Bps */
    double download_speed_KBps;

    gboolean compact;
};

/***
****
***/

static GdkPixbuf*
get_icon( const tr_torrent * tor, GtkIconSize icon_size, GtkWidget * for_widget )
{
    const char * mime_type;
    const tr_info * info = tr_torrentInfo( tor );

    if( info->fileCount == 0  )
        mime_type = UNKNOWN_MIME_TYPE;
    else if( info->fileCount > 1 )
        mime_type = DIRECTORY_MIME_TYPE;
    else if( strchr( info->files[0].name, '/' ) != NULL )
        mime_type = DIRECTORY_MIME_TYPE;
    else
        mime_type = gtr_get_mime_type_from_filename( info->files[0].name );

    return gtr_get_mime_type_icon( mime_type, icon_size, for_widget );
}

/***
****
***/

static void
get_size_compact( TorrentCellRenderer * cell,
                  GtkWidget           * widget,
                  gint                * width,
                  gint                * height )
{
    int w, h;
    int xpad, ypad;
    GdkRectangle icon_area;
    GdkRectangle name_area;
    GdkRectangle stat_area;
    const char * name;
    char * status;
    GdkPixbuf * icon;

    struct TorrentCellRendererPrivate * p = cell->priv;
    const tr_torrent * tor = p->tor;
    const tr_stat * st = tr_torrentStatCached( (tr_torrent*)tor );

    icon = get_icon( tor, COMPACT_ICON_SIZE, widget );
    name = tr_torrentInfo( tor )->name;
    status = getShortStatusString( tor, st, p->upload_speed_KBps, p->download_speed_KBps );
    gtr_cell_renderer_get_padding( GTK_CELL_RENDERER( cell ), &xpad, &ypad );

    /* get the idealized cell dimensions */
    g_object_set( p->icon_renderer, "pixbuf", icon, NULL );
    gtk_cell_renderer_get_size( p->icon_renderer, widget, NULL, NULL, NULL, &w, &h );
    icon_area.width = w;
    icon_area.height = h;
    g_object_set( p->text_renderer, "text", name, "ellipsize", PANGO_ELLIPSIZE_NONE,  "scale", 1.0, NULL );
    gtk_cell_renderer_get_size( p->text_renderer, widget, NULL, NULL, NULL, &w, &h );
    name_area.width = w;
    name_area.height = h;
    g_object_set( p->text_renderer, "text", status, "scale", SMALL_SCALE, NULL );
    gtk_cell_renderer_get_size( p->text_renderer, widget, NULL, NULL, NULL, &w, &h );
    stat_area.width = w;
    stat_area.height = h;

    /**
    *** LAYOUT
    **/

#define BAR_WIDTH 50
    if( width != NULL )
        *width = xpad * 2 + icon_area.width + GUI_PAD + name_area.width + GUI_PAD + BAR_WIDTH + GUI_PAD + stat_area.width;
    if( height != NULL )
        *height = ypad * 2 + MAX( name_area.height, p->bar_height );

    /* cleanup */
    g_free( status );
    g_object_unref( icon );
}

#define MAX3(a,b,c) MAX(a,MAX(b,c))

static void
get_size_full( TorrentCellRenderer * cell,
               GtkWidget           * widget,
               gint                * width,
               gint                * height )
{
    int w, h;
    int xpad, ypad;
    GdkRectangle icon_area;
    GdkRectangle name_area;
    GdkRectangle stat_area;
    GdkRectangle prog_area;
    const char * name;
    char * status;
    char * progress;
    GdkPixbuf * icon;

    struct TorrentCellRendererPrivate * p = cell->priv;
    const tr_torrent * tor = p->tor;
    const tr_stat * st = tr_torrentStatCached( (tr_torrent*)tor );
    const tr_info * inf = tr_torrentInfo( tor );

    icon = get_icon( tor, FULL_ICON_SIZE, widget );
    name = inf->name;
    status = getStatusString( tor, st, p->upload_speed_KBps, p->download_speed_KBps );
    progress = getProgressString( tor, inf, st );
    gtr_cell_renderer_get_padding( GTK_CELL_RENDERER( cell ), &xpad, &ypad );

    /* get the idealized cell dimensions */
    g_object_set( p->icon_renderer, "pixbuf", icon, NULL );
    gtk_cell_renderer_get_size( p->icon_renderer, widget, NULL, NULL, NULL, &w, &h );
    icon_area.width = w;
    icon_area.height = h;
    g_object_set( p->text_renderer, "text", name, "weight", PANGO_WEIGHT_BOLD, "scale", 1.0, "ellipsize", PANGO_ELLIPSIZE_NONE, NULL );
    gtk_cell_renderer_get_size( p->text_renderer, widget, NULL, NULL, NULL, &w, &h );
    name_area.width = w;
    name_area.height = h;
    g_object_set( p->text_renderer, "text", progress, "weight", PANGO_WEIGHT_NORMAL, "scale", SMALL_SCALE, NULL );
    gtk_cell_renderer_get_size( p->text_renderer, widget, NULL, NULL, NULL, &w, &h );
    prog_area.width = w;
    prog_area.height = h;
    g_object_set( p->text_renderer, "text", status, NULL );
    gtk_cell_renderer_get_size( p->text_renderer, widget, NULL, NULL, NULL, &w, &h );
    stat_area.width = w;
    stat_area.height = h;

    /**
    *** LAYOUT
    **/

    if( width != NULL )
        *width = xpad * 2 + icon_area.width + GUI_PAD + MAX3( name_area.width, prog_area.width, stat_area.width );
    if( height != NULL )
        *height = ypad * 2 + name_area.height + prog_area.height + GUI_PAD_SMALL + p->bar_height + GUI_PAD_SMALL + stat_area.height;

    /* cleanup */
    g_free( status );
    g_free( progress );
    g_object_unref( icon );
}


static void
torrent_cell_renderer_get_size( GtkCellRenderer  * cell,
                                GtkWidget        * widget,
                                GdkRectangle     * cell_area,
                                gint             * x_offset,
                                gint             * y_offset,
                                gint             * width,
                                gint             * height )
{
    TorrentCellRenderer * self = TORRENT_CELL_RENDERER( cell );

    if( self && self->priv->tor )
    {
        int w, h;
        struct TorrentCellRendererPrivate * p = self->priv;

        if( p->compact )
            get_size_compact( TORRENT_CELL_RENDERER( cell ), widget, &w, &h );
        else
            get_size_full( TORRENT_CELL_RENDERER( cell ), widget, &w, &h );

        if( width )
            *width = w;

        if( height )
            *height = h;

        if( x_offset )
            *x_offset = cell_area ? cell_area->x : 0;

        if( y_offset ) {
            int xpad, ypad;
            gtr_cell_renderer_get_padding( cell, &xpad, &ypad );
            *y_offset = cell_area ? (int)((cell_area->height - (ypad*2 +h)) / 2.0) : 0;
        }
    }
}

static void
get_text_color( GtkWidget * w, const tr_stat * st, GdkColor * setme )
{
    static const GdkColor red = { 0, 65535, 0, 0 };

    if( st->error )
        *setme = red;
    else if( st->activity == TR_STATUS_STOPPED )
        *setme = gtk_widget_get_style(w)->text[GTK_STATE_INSENSITIVE];
    else
        *setme = gtk_widget_get_style(w)->text[GTK_STATE_NORMAL];
}

static void
render_compact( TorrentCellRenderer   * cell,
                GdkDrawable           * window,
                GtkWidget             * widget,
                GdkRectangle          * background_area,
                GdkRectangle          * cell_area UNUSED,
                GdkRectangle          * expose_area UNUSED,
                GtkCellRendererState    flags )
{
    int xpad, ypad;
    GdkRectangle icon_area;
    GdkRectangle name_area;
    GdkRectangle stat_area;
    GdkRectangle prog_area;
    GdkRectangle fill_area;
    const char * name;
    char * status;
    GdkPixbuf * icon;
    GdkColor text_color;

    struct TorrentCellRendererPrivate * p = cell->priv;
    const tr_torrent * tor = p->tor;
    const tr_stat * st = tr_torrentStatCached( (tr_torrent*)tor );
    const gboolean active = st->activity != TR_STATUS_STOPPED;
    const double percentDone = MAX( 0.0, st->percentDone );
    const gboolean sensitive = active || st->error;

    icon = get_icon( tor, COMPACT_ICON_SIZE, widget );
    name = tr_torrentInfo( tor )->name;
    status = getShortStatusString( tor, st, p->upload_speed_KBps, p->download_speed_KBps );
    gtr_cell_renderer_get_padding( GTK_CELL_RENDERER( cell ), &xpad, &ypad );
    get_text_color( widget, st, &text_color );

    fill_area = *background_area;
    fill_area.x += xpad;
    fill_area.y += ypad;
    fill_area.width -= xpad * 2;
    fill_area.height -= ypad * 2;
    icon_area = name_area = stat_area = prog_area = fill_area;

    g_object_set( p->icon_renderer, "pixbuf", icon, NULL );
    gtk_cell_renderer_get_size( p->icon_renderer, widget, NULL, NULL, NULL, &icon_area.width, NULL );
    g_object_set( p->text_renderer, "text", name, "ellipsize", PANGO_ELLIPSIZE_NONE, "scale", 1.0, NULL );
    gtk_cell_renderer_get_size( p->text_renderer, widget, NULL, NULL, NULL, &name_area.width, NULL );
    g_object_set( p->text_renderer, "text", status, "scale", SMALL_SCALE, NULL );
    gtk_cell_renderer_get_size( p->text_renderer, widget, NULL, NULL, NULL, &stat_area.width, NULL );

    icon_area.x = fill_area.x;
    prog_area.x = fill_area.x + fill_area.width - BAR_WIDTH;
    prog_area.width = BAR_WIDTH;
    stat_area.x = prog_area.x - GUI_PAD - stat_area.width;
    name_area.x = icon_area.x + icon_area.width + GUI_PAD;
    name_area.y = fill_area.y;
    name_area.width = stat_area.x - GUI_PAD - name_area.x;

    /**
    *** RENDER
    **/

    g_object_set( p->icon_renderer, "pixbuf", icon, "sensitive", sensitive, NULL );
    gtk_cell_renderer_render( p->icon_renderer, window, widget, &icon_area, &icon_area, &icon_area, flags );
    g_object_set( p->progress_renderer, "value", (int)(percentDone*100.0), "text", NULL, "sensitive", sensitive, NULL );
    gtk_cell_renderer_render( p->progress_renderer, window, widget, &prog_area, &prog_area, &prog_area, flags );
    g_object_set( p->text_renderer, "text", status, "scale", SMALL_SCALE, "ellipsize", PANGO_ELLIPSIZE_END, "foreground-gdk", &text_color, NULL );
    gtk_cell_renderer_render( p->text_renderer, window, widget, &stat_area, &stat_area, &stat_area, flags );
    g_object_set( p->text_renderer, "text", name, "scale", 1.0, NULL );
    gtk_cell_renderer_render( p->text_renderer, window, widget, &name_area, &name_area, &name_area, flags );

    /* cleanup */
    g_free( status );
    g_object_unref( icon );
}

static void
render_full( TorrentCellRenderer   * cell,
             GdkDrawable           * window,
             GtkWidget             * widget,
             GdkRectangle          * background_area,
             GdkRectangle          * cell_area UNUSED,
             GdkRectangle          * expose_area UNUSED,
             GtkCellRendererState    flags )
{
    int w, h;
    int xpad, ypad;
    GdkRectangle fill_area;
    GdkRectangle icon_area;
    GdkRectangle name_area;
    GdkRectangle stat_area;
    GdkRectangle prog_area;
    GdkRectangle prct_area;
    const char * name;
    char * status;
    char * progress;
    GdkPixbuf * icon;
    GdkColor text_color;

    struct TorrentCellRendererPrivate * p = cell->priv;
    const tr_torrent * tor = p->tor;
    const tr_stat * st = tr_torrentStatCached( (tr_torrent*)tor );
    const tr_info * inf = tr_torrentInfo( tor );
    const gboolean active = st->activity != TR_STATUS_STOPPED;
    const double percentDone = MAX( 0.0, st->percentDone );
    const gboolean sensitive = active || st->error;

    icon = get_icon( tor, FULL_ICON_SIZE, widget );
    name = inf->name;
    status = getStatusString( tor, st, p->upload_speed_KBps, p->download_speed_KBps );
    progress = getProgressString( tor, inf, st );
    gtr_cell_renderer_get_padding( GTK_CELL_RENDERER( cell ), &xpad, &ypad );
    get_text_color( widget, st, &text_color );

    /* get the idealized cell dimensions */
    g_object_set( p->icon_renderer, "pixbuf", icon, NULL );
    gtk_cell_renderer_get_size( p->icon_renderer, widget, NULL, NULL, NULL, &w, &h );
    icon_area.width = w;
    icon_area.height = h;
    g_object_set( p->text_renderer, "text", name, "weight", PANGO_WEIGHT_BOLD, "ellipsize", PANGO_ELLIPSIZE_NONE, "scale", 1.0, NULL );
    gtk_cell_renderer_get_size( p->text_renderer, widget, NULL, NULL, NULL, &w, &h );
    name_area.width = w;
    name_area.height = h;
    g_object_set( p->text_renderer, "text", progress, "weight", PANGO_WEIGHT_NORMAL, "scale", SMALL_SCALE, NULL );
    gtk_cell_renderer_get_size( p->text_renderer, widget, NULL, NULL, NULL, &w, &h );
    prog_area.width = w;
    prog_area.height = h;
    g_object_set( p->text_renderer, "text", status, NULL );
    gtk_cell_renderer_get_size( p->text_renderer, widget, NULL, NULL, NULL, &w, &h );
    stat_area.width = w;
    stat_area.height = h;

    /**
    *** LAYOUT
    **/

    fill_area = *background_area;
    fill_area.x += xpad;
    fill_area.y += ypad;
    fill_area.width -= xpad * 2;
    fill_area.height -= ypad * 2;

    /* icon */
    icon_area.x = fill_area.x;
    icon_area.y = fill_area.y + ( fill_area.height - icon_area.height ) / 2;

    /* name */
    name_area.x = icon_area.x + icon_area.width + GUI_PAD;
    name_area.y = fill_area.y;
    name_area.width = fill_area.width - GUI_PAD - icon_area.width - GUI_PAD_SMALL;

    /* prog */
    prog_area.x = name_area.x;
    prog_area.y = name_area.y + name_area.height;
    prog_area.width = name_area.width;

    /* progressbar */
    prct_area.x = prog_area.x;
    prct_area.y = prog_area.y + prog_area.height + GUI_PAD_SMALL;
    prct_area.width = prog_area.width;
    prct_area.height = p->bar_height;

    /* status */
    stat_area.x = prct_area.x;
    stat_area.y = prct_area.y + prct_area.height + GUI_PAD_SMALL;
    stat_area.width = prct_area.width;

    /**
    *** RENDER
    **/

    g_object_set( p->icon_renderer, "pixbuf", icon, "sensitive", sensitive, NULL );
    gtk_cell_renderer_render( p->icon_renderer, window, widget, &icon_area, &icon_area, &icon_area, flags );
    g_object_set( p->text_renderer, "text", name, "scale", 1.0, "foreground-gdk", &text_color, "ellipsize", PANGO_ELLIPSIZE_END, "weight", PANGO_WEIGHT_BOLD, NULL );
    gtk_cell_renderer_render( p->text_renderer, window, widget, &name_area, &name_area, &name_area, flags );
    g_object_set( p->text_renderer, "text", progress, "scale", SMALL_SCALE, "weight", PANGO_WEIGHT_NORMAL, NULL );
    gtk_cell_renderer_render( p->text_renderer, window, widget, &prog_area, &prog_area, &prog_area, flags );
    g_object_set( p->progress_renderer, "value", (int)(percentDone*100.0), "text", "", "sensitive", sensitive, NULL );
    gtk_cell_renderer_render( p->progress_renderer, window, widget, &prct_area, &prct_area, &prct_area, flags );
    g_object_set( p->text_renderer, "text", status, NULL );
    gtk_cell_renderer_render( p->text_renderer, window, widget, &stat_area, &stat_area, &stat_area, flags );

    /* cleanup */
    g_free( status );
    g_free( progress );
    g_object_unref( icon );
}

static void
torrent_cell_renderer_render( GtkCellRenderer       * cell,
                              GdkDrawable           * window,
                              GtkWidget             * widget,
                              GdkRectangle          * background_area,
                              GdkRectangle          * cell_area,
                              GdkRectangle          * expose_area,
                              GtkCellRendererState    flags )
{
    TorrentCellRenderer * self = TORRENT_CELL_RENDERER( cell );

#ifdef TEST_RTL
    GtkTextDirection      real_dir = gtk_widget_get_direction( widget );
    gtk_widget_set_direction( widget, GTK_TEXT_DIR_RTL );
#endif

    if( self && self->priv->tor )
    {
        struct TorrentCellRendererPrivate * p = self->priv;
        if( p->compact )
            render_compact( self, window, widget, background_area, cell_area, expose_area, flags );
        else
            render_full( self, window, widget, background_area, cell_area, expose_area, flags );
    }

#ifdef TEST_RTL
    gtk_widget_set_direction( widget, real_dir );
#endif
}

static void
torrent_cell_renderer_set_property( GObject      * object,
                                    guint          property_id,
                                    const GValue * v,
                                    GParamSpec   * pspec )
{
    TorrentCellRenderer * self = TORRENT_CELL_RENDERER( object );
    struct TorrentCellRendererPrivate * p = self->priv;

    switch( property_id )
    {
        case P_TORRENT:        p->tor                 = g_value_get_pointer( v ); break;
        case P_UPLOAD_SPEED:   p->upload_speed_KBps   = g_value_get_double( v ); break;
        case P_DOWNLOAD_SPEED: p->download_speed_KBps = g_value_get_double( v ); break;
        case P_BAR_HEIGHT:     p->bar_height          = g_value_get_int( v ); break;
        case P_COMPACT:        p->compact             = g_value_get_boolean( v ); break;
        default: G_OBJECT_WARN_INVALID_PROPERTY_ID( object, property_id, pspec ); break;
    }
}

static void
torrent_cell_renderer_get_property( GObject     * object,
                                    guint         property_id,
                                    GValue      * v,
                                    GParamSpec  * pspec )
{
    const TorrentCellRenderer * self = TORRENT_CELL_RENDERER( object );
    struct TorrentCellRendererPrivate * p = self->priv;

    switch( property_id )
    {
        case P_TORRENT:        g_value_set_pointer( v, p->tor ); break;
        case P_UPLOAD_SPEED:   g_value_set_double( v, p->upload_speed_KBps ); break;
        case P_DOWNLOAD_SPEED: g_value_set_double( v, p->download_speed_KBps ); break;
        case P_BAR_HEIGHT:     g_value_set_int( v, p->bar_height ); break;
        case P_COMPACT:        g_value_set_boolean( v, p->compact ); break;
        default: G_OBJECT_WARN_INVALID_PROPERTY_ID( object, property_id, pspec ); break;
    }
}

static void
torrent_cell_renderer_dispose( GObject * o )
{
    TorrentCellRenderer * r = TORRENT_CELL_RENDERER( o );
    GObjectClass *        parent;

    if( r && r->priv )
    {
        g_object_unref( G_OBJECT( r->priv->text_renderer ) );
        g_object_unref( G_OBJECT( r->priv->progress_renderer ) );
        g_object_unref( G_OBJECT( r->priv->icon_renderer ) );
        r->priv = NULL;
    }

    parent = g_type_class_peek( g_type_parent( TORRENT_CELL_RENDERER_TYPE ) );
    parent->dispose( o );
}

static void
torrent_cell_renderer_class_init( TorrentCellRendererClass * klass )
{
    GObjectClass *         gobject_class = G_OBJECT_CLASS( klass );
    GtkCellRendererClass * cell_class = GTK_CELL_RENDERER_CLASS( klass );

    g_type_class_add_private( klass,
                             sizeof( struct TorrentCellRendererPrivate ) );

    parent_class = (GtkCellRendererClass*) g_type_class_peek_parent( klass );

    cell_class->render = torrent_cell_renderer_render;
    cell_class->get_size = torrent_cell_renderer_get_size;
    gobject_class->set_property = torrent_cell_renderer_set_property;
    gobject_class->get_property = torrent_cell_renderer_get_property;
    gobject_class->dispose = torrent_cell_renderer_dispose;

    g_object_class_install_property( gobject_class, P_TORRENT,
                                    g_param_spec_pointer( "torrent", NULL,
                                                          "tr_torrent*",
                                                          G_PARAM_READWRITE ) );

    g_object_class_install_property( gobject_class, P_UPLOAD_SPEED,
                                    g_param_spec_double( "piece-upload-speed", NULL,
                                                         "tr_stat.pieceUploadSpeed_KBps",
                                                         0, INT_MAX, 0,
                                                         G_PARAM_READWRITE ) );

    g_object_class_install_property( gobject_class, P_DOWNLOAD_SPEED,
                                    g_param_spec_double( "piece-download-speed", NULL,
                                                         "tr_stat.pieceDownloadSpeed_KBps",
                                                         0, INT_MAX, 0,
                                                         G_PARAM_READWRITE ) );

    g_object_class_install_property( gobject_class, P_BAR_HEIGHT,
                                    g_param_spec_int( "bar-height", NULL,
                                                      "Bar Height",
                                                      1, INT_MAX,
                                                      DEFAULT_BAR_HEIGHT,
                                                      G_PARAM_READWRITE ) );

    g_object_class_install_property( gobject_class, P_COMPACT,
                                    g_param_spec_boolean( "compact", NULL,
                                                          "Compact Mode",
                                                          FALSE,
                                                          G_PARAM_READWRITE ) );
}

static void
torrent_cell_renderer_init( GTypeInstance *  instance,
                            gpointer g_class UNUSED )
{
    TorrentCellRenderer *               self = TORRENT_CELL_RENDERER(
        instance );
    struct TorrentCellRendererPrivate * p;

    p = self->priv = G_TYPE_INSTANCE_GET_PRIVATE(
            self,
            TORRENT_CELL_RENDERER_TYPE,
            struct
            TorrentCellRendererPrivate );

    p->tor = NULL;
    p->text_renderer = gtk_cell_renderer_text_new( );
    g_object_set( p->text_renderer, "xpad", 0, "ypad", 0, NULL );
    p->progress_renderer = gtk_cell_renderer_progress_new(  );
    p->icon_renderer = gtk_cell_renderer_pixbuf_new(  );
    gtr_object_ref_sink( p->text_renderer );
    gtr_object_ref_sink( p->progress_renderer );
    gtr_object_ref_sink( p->icon_renderer );

    p->bar_height = DEFAULT_BAR_HEIGHT;
}

GType
torrent_cell_renderer_get_type( void )
{
    static GType type = 0;

    if( !type )
    {
        static const GTypeInfo info =
        {
            sizeof( TorrentCellRendererClass ),
            NULL,                                            /* base_init */
            NULL,                                            /* base_finalize */
            (GClassInitFunc)torrent_cell_renderer_class_init,
            NULL,                                            /* class_finalize
                                                               */
            NULL,                                            /* class_data */
            sizeof( TorrentCellRenderer ),
            0,                                               /* n_preallocs */
            (GInstanceInitFunc)torrent_cell_renderer_init,
            NULL
        };

        type = g_type_register_static( GTK_TYPE_CELL_RENDERER,
                                       "TorrentCellRenderer",
                                       &info, (GTypeFlags)0 );
    }

    return type;
}

GtkCellRenderer *
torrent_cell_renderer_new( void )
{
    return (GtkCellRenderer *) g_object_new( TORRENT_CELL_RENDERER_TYPE,
                                             NULL );
}

