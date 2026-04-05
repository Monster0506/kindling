import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'intro',
    'getting-started',
    {
      type: 'category',
      label: 'Guides',
      collapsed: false,
      items: [
        'routing',
        'live-pages',
        'reactive-ui',
        'client-runtime',
        'demos',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: ['architecture', 'api'],
    },
  ],
};

export default sidebars;
