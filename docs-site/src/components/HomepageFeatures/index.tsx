import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Routing and Jinja',
    description: (
      <>
        Register handlers with <code>@app.get</code> and <code>@app.post</code>. Render
        templates with <code>Application(template_dir=...)</code> and optional path
        parameters.
      </>
    ),
  },
  {
    title: 'Live pages',
    description: (
      <>
        One URL for GET and POST: morph updates in the browser with Idiomorph, optional
        JSON config injection, and <code>/_kindling/client.js</code>.
      </>
    ),
  },
  {
    title: 'Reactive scopes',
    description: (
      <>
        <code>signal</code>, <code>@bind</code>, <code>@live</code>, and <code>@on</code> with
        SSE snapshots for server-driven DOM sync when you need it.
      </>
    ),
  },
];

function Feature({title, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
