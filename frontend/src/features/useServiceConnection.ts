import {useEffect, useState} from 'react';
import {getApi, type Options, type Capabilities} from '../api';
import {useApiTask} from './useApiTask';

export function useServiceConnection() {
  const options = useApiTask<Options>();
  const capabilities = useApiTask<Capabilities>();
  const [attempt, setAttempt] = useState(0);
  const loadOptions = options.run;
  const loadCapabilities = capabilities.run;
  useEffect(() => {
    void loadOptions(signal => getApi<Options>('/options', signal));
    void loadCapabilities(signal => getApi<Capabilities>('/capabilities', signal));
  }, [attempt, loadOptions, loadCapabilities]);
  function reconnect() {
    options.reset();
    capabilities.reset();
    setAttempt(value => value + 1);
  }
  return {options, capabilities, reconnect};
}
