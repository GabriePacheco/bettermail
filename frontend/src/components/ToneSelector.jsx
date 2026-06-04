export default function ToneSelector({ tone, onChange }) {
  return (
    <div className="tone-selector">
      <label htmlFor="tone">Tono del correo</label>
      <select id="tone" value={tone} onChange={(event) => onChange(event.target.value)}>
        <option value="neutral">Neutral</option>
        <option value="friendly">Amistoso</option>
        <option value="formal">Formal</option>
        <option value="assertive">Asertivo</option>
      </select>
    </div>
  )
}
