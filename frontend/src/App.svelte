<script>
  import { onMount } from 'svelte';

  let tower = $state(null);
  let connected = $state(false);

  onMount(() => {
    const source = new EventSource('/timing');
    source.onopen = () => (connected = true);
    source.onerror = () => (connected = false);
    source.onmessage = (event) => {
      tower = JSON.parse(event.data);
    };
    return () => source.close();
  });

  const formatInterval = (value) => (value == null ? 'Leader' : `+${value.toFixed(3)}`);
</script>


<main>
  <h1>F1 Timing Tower</h1>
  <p class="status">
    {connected ? 'Connected' : 'Disconnected'}
    {#if tower}
      | Lap {tower.lap ?? '-'} | {tower.at}
    {/if}
  </p>

  {#if tower}
    <table>
      <thead>
        <tr><th>Pos</th><th>No.</th><th>Driver</th><th>Interval</th></tr>
      </thead>
      <tbody>
        {#each tower.rows as row (row.driver_number)}
          <tr>
            <td>{row.position}</td>
            <td>{row.driver_number}</td>
            <td>{row.driver_name}</td>
            <td>{formatInterval(row.interval)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {:else}
    <p>Waiting for data...</p>
  {/if}
</main>


<style>
  main { font-family: system-ui, sans-serif; max-width: 480px; margin: 2rem auto; }
  .status { color: #666; font-size: 0.9rem; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid #ddd; }
</style>
