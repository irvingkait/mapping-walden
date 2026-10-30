// App.jsx: the top of the app. It does two things:
//   1. loads walden.json (the data that Python built), showing "Loading" until it arrives;
//   2. once it has the data, shows <Walden />, the map and its controls.
import { useEffect, useState } from "react";
import Walden from "./Walden.jsx";

export default function App() {
  const [data, setData] = useState(null);       // null until the file arrives
  const [error, setError] = useState(null);

  useEffect(() => {
    // import.meta.env.BASE_URL is the folder the app is served from ("./" for us), so this works on any web host.
    fetch(import.meta.env.BASE_URL + "data/walden.json")
      .then(r => { if (!r.ok) throw new Error("walden.json not found (" + r.status + "). Did you run build_data.py?"); return r.json(); })
      .then(setData)
      .catch(e => setError(String(e.message || e)));
  }, []);                                       // [] = do this once, when the app first appears

  if (error) return <div className="status">Could not load the data. {error}</div>;
  if (!data) return <div className="status">Loading the path of Walden&hellip;</div>;
  return <Walden D={data} />;
}
