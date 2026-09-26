/** @type {import('electron-builder').Configuration} */
module.exports = {
  appId: 'com.kofvictory.kofpro',
  productName: 'KofPro',
  copyright: 'Copyright © 2026 kofvictory',

  directories: {
    output: 'dist',
    buildResources: 'build-resources',
  },

  // Electron main entry (compiled from electron/main.ts)
  main: 'dist-electron/main.js',

  // Files to include in the app bundle
  files: [
    'dist-electron/**/*',
    'package.json',
    // Next.js standalone server and static assets
    '.next/standalone/**/*',
    '.next/static/**/*',
    'public/**/*',
  ],

  // Next.js standalone output goes to resources/app/
  extraResources: [
    {
      from: '.next/standalone',
      to: 'app/.next/standalone',
    },
    {
      from: '.next/static',
      to: 'app/.next/standalone/.next/static',
    },
    {
      from: 'public',
      to: 'app/.next/standalone/public',
    },
  ],

  win: {
    target: [
      // ARM64 for Snapdragon X, x64 for Intel/AMD
      { target: 'nsis', arch: ['arm64', 'x64'] },
    ],
    artifactName: '${productName}-${version}-${arch}-setup.${ext}',
  },

  nsis: {
    oneClick: false,
    allowToChangeInstallationDirectory: true,
    createDesktopShortcut: true,
    createStartMenuShortcut: true,
  },

  mac: {
    target: [{ target: 'dmg', arch: ['arm64', 'x64'] }],
    category: 'public.app-category.productivity',
    artifactName: '${productName}-${version}-${arch}.${ext}',
  },

  linux: {
    target: ['AppImage'],
    category: 'Utility',
  },
}
