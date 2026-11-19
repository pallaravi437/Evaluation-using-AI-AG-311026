package com.aievaluator.app;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.File;
import java.io.FileNotFoundException;

public class AppFileProvider extends ContentProvider {
    public static final String AUTHORITY = "com.aievaluator.app.fileprovider";

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        File file = new File(getContext().getCacheDir(), uri.getLastPathSegment());
        if (!file.exists()) {
            try {
                file.createNewFile();
            } catch (Exception ignored) {}
        }
        return ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_WRITE | ParcelFileDescriptor.MODE_CREATE);
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        File file = new File(getContext().getCacheDir(), uri.getLastPathSegment());
        MatrixCursor cursor = new MatrixCursor(new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE});
        cursor.addRow(new Object[]{file.getName(), file.length()});
        return cursor;
    }

    @Override
    public String getType(Uri uri) {
        String name = uri.getLastPathSegment();
        if (name != null && name.endsWith(".png")) return "image/png";
        if (name != null && name.endsWith(".pdf")) return "application/pdf";
        return "image/jpeg";
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        return null;
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        File file = new File(getContext().getCacheDir(), uri.getLastPathSegment());
        if (file.exists()) {
            return file.delete() ? 1 : 0;
        }
        return 0;
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        return 0;
    }
}
