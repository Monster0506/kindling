import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Kindling',
  tagline: 'Python web layer with routes, Jinja, and optional live reactive UI',
  favicon: 'img/logo.svg',
  url: 'https://kindling.example.com',
  baseUrl: '/',

  organizationName: 'kindling',
  projectName: 'kindling',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: 'docs',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'Kindling',
      logo: {
        alt: 'Kindling',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Documentation',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'Introduction', to: '/docs/intro'},
            {label: 'Getting started', to: '/docs/getting-started'},
            {label: 'Reactive UI', to: '/docs/reactive-ui'},
          ],
        },
        {
          title: 'Project',
          items: [{label: 'Demos', to: '/docs/demos'}],
        },
      ],
      copyright: `Copyright ${new Date().getFullYear()} Kindling contributors. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'python'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
