package com.aievaluator.app;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.PermissionRequest;
import android.webkit.SslErrorHandler;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;

public class MainActivity extends Activity {

    private WebView mWebView;
    private ProgressBar mProgressBar;
    private LinearLayout mErrorLayout;
    private ValueCallback<Uri[]> mUploadMessage;
    private Uri mCameraPhotoUri;
    private long mLastBackPressTime = 0;

    private static final int FILECHOOSER_RESULTCODE = 101;
    private static final int PERMISSION_REQUEST_CODE = 202;
    private static final String APP_URL = "https://online-ai-evaluator.onrender.com";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Root FrameLayout
        FrameLayout rootLayout = new FrameLayout(this);
        rootLayout.setBackgroundColor(0xFF0F172A); // slate-900

        // 1. WebView
        mWebView = new WebView(this);
        mWebView.setBackgroundColor(0xFF0F172A);
        rootLayout.addView(mWebView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        // 2. ProgressBar
        mProgressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        mProgressBar.setIndeterminate(false);
        mProgressBar.setMax(100);
        mProgressBar.setProgress(0);
        FrameLayout.LayoutParams pbParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, 8);
        rootLayout.addView(mProgressBar, pbParams);

        // 3. Error / Retry Overlay
        mErrorLayout = new LinearLayout(this);
        mErrorLayout.setOrientation(LinearLayout.VERTICAL);
        mErrorLayout.setGravity(android.view.Gravity.CENTER);
        mErrorLayout.setBackgroundColor(0xFF0F172A);
        mErrorLayout.setVisibility(View.GONE);

        TextView errText = new TextView(this);
        errText.setText("Connecting to Online AI Evaluator...\nIf server was sleeping, please wait a moment.");
        errText.setTextColor(0xFFE2E8F0);
        errText.setTextSize(16);
        errText.setGravity(android.view.Gravity.CENTER);
        errText.setPadding(32, 16, 32, 24);
        mErrorLayout.addView(errText);

        Button retryBtn = new Button(this);
        retryBtn.setText("Retry Connection");
        retryBtn.setBackgroundColor(0xFF4F46E5);
        retryBtn.setTextColor(0xFFFFFFFF);
        retryBtn.setPadding(48, 16, 48, 16);
        retryBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                mErrorLayout.setVisibility(View.GONE);
                mWebView.loadUrl(APP_URL);
            }
        });
        mErrorLayout.addView(retryBtn);

        rootLayout.addView(mErrorLayout, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        setContentView(rootLayout);

        setupWebSettings();
        setupClients();

        // Check runtime permissions for Android 6.0+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (checkSelfPermission(android.Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{android.Manifest.permission.CAMERA}, PERMISSION_REQUEST_CODE);
            }
        }

        mWebView.loadUrl(APP_URL);
    }

    private void setupWebSettings() {
        WebSettings s = mWebView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setSupportZoom(true);
        s.setBuiltInZoomControls(true);
        s.setDisplayZoomControls(false);
        s.setSaveFormData(true);
        s.setMediaPlaybackRequiresUserGesture(false);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setUserAgentString(s.getUserAgentString() + " AIEvaluatorAndroid/1.0");
    }

    private void setupClients() {
        mWebView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                if (url.startsWith("http://") || url.startsWith("https://")) {
                    view.loadUrl(url);
                    return true;
                }
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                    return true;
                } catch (Exception e) {
                    return false;
                }
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                mProgressBar.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                mProgressBar.setVisibility(View.GONE);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    mProgressBar.setVisibility(View.GONE);
                    mErrorLayout.setVisibility(View.VISIBLE);
                }
            }

            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                // Ensure cloud host SSL certificates never block the app on older or non-standard devices
                handler.proceed();
            }
        });

        mWebView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                mProgressBar.setProgress(newProgress);
                if (newProgress == 100) {
                    mProgressBar.setVisibility(View.GONE);
                } else {
                    mProgressBar.setVisibility(View.VISIBLE);
                }
            }

            @Override
            public void onPermissionRequest(PermissionRequest request) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                    request.grant(request.getResources());
                }
            }

            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback,
                                            FileChooserParams fileChooserParams) {
                if (mUploadMessage != null) {
                    mUploadMessage.onReceiveValue(null);
                }
                mUploadMessage = filePathCallback;

                Intent takePictureIntent = null;
                try {
                    File photoFile = new File(getCacheDir(), "camera_photo_" + System.currentTimeMillis() + ".jpg");
                    mCameraPhotoUri = Uri.parse("content://" + AppFileProvider.AUTHORITY + "/" + photoFile.getName());
                    takePictureIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
                    takePictureIntent.putExtra(MediaStore.EXTRA_OUTPUT, mCameraPhotoUri);
                    takePictureIntent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
                } catch (Exception ignored) {}

                Intent contentSelectionIntent = fileChooserParams.createIntent();
                Intent[] intentArray;
                if (takePictureIntent != null) {
                    intentArray = new Intent[]{takePictureIntent};
                } else {
                    intentArray = new Intent[0];
                }

                Intent chooserIntent = new Intent(Intent.ACTION_CHOOSER);
                chooserIntent.putExtra(Intent.EXTRA_INTENT, contentSelectionIntent);
                chooserIntent.putExtra(Intent.EXTRA_TITLE, "Upload Answer Sheet (Camera or Files)");
                chooserIntent.putExtra(Intent.EXTRA_INITIAL_INTENTS, intentArray);

                try {
                    startActivityForResult(chooserIntent, FILECHOOSER_RESULTCODE);
                } catch (Exception e) {
                    mUploadMessage = null;
                    Toast.makeText(MainActivity.this, "Cannot open file picker", Toast.LENGTH_SHORT).show();
                    return false;
                }
                return true;
            }
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILECHOOSER_RESULTCODE) {
            if (mUploadMessage == null) return;
            Uri[] results = null;

            if (resultCode == Activity.RESULT_OK) {
                if (data == null || data.getData() == null) {
                    // Result came from camera
                    if (mCameraPhotoUri != null) {
                        results = new Uri[]{mCameraPhotoUri};
                    }
                } else {
                    results = WebChromeClient.FileChooserParams.parseResult(resultCode, data);
                }
            }
            mUploadMessage.onReceiveValue(results);
            mUploadMessage = null;
            mCameraPhotoUri = null;
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (mWebView != null && mWebView.canGoBack()) {
                mWebView.goBack();
                return true;
            } else {
                long currentTime = System.currentTimeMillis();
                if (currentTime - mLastBackPressTime < 2000) {
                    finish();
                } else {
                    mLastBackPressTime = currentTime;
                    Toast.makeText(this, "Press back again to exit", Toast.LENGTH_SHORT).show();
                }
                return true;
            }
        }
        return super.onKeyDown(keyCode, event);
    }
}
